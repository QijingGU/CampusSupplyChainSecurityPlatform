from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session

from ..api.deps import require_roles
from ..database import get_db
from ..models.audit_log import AuditLog
from ..models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])
_allowed = require_roles("system_admin")

IDS_ACTION_PREFIX = "ids_"
SENSITIVE_ACTIONS = {
    "purchase_reject",
    "supplier_confirm",
    "warning_handle",
    "ids_source_package_activate",
    "ids_source_package_activate_rejected",
    "ids_rulepack_activate",
    "ids_rulepack_activate_rejected",
    "ids_rulepack_activate_failed",
}


@router.get("")
def list_audit_logs(
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    user_name: str | None = Query(None),
    keyword: str | None = Query(None),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    ids_only: int = Query(0, ge=0, le=1),
    sensitive_only: int = Query(0, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(_allowed),
):
    if start_at and end_at and start_at > end_at:
        raise HTTPException(status_code=400, detail="start_at must be earlier than end_at")

    q = db.query(AuditLog)
    q = _apply_audit_filters(
        q,
        action=action,
        target_type=target_type,
        user_name=user_name,
        keyword=keyword,
        start_at=start_at,
        end_at=end_at,
        ids_only=bool(ids_only),
        sensitive_only=bool(sensitive_only),
    )

    total = q.count()
    items = (
        q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    summary = _build_summary(q)
    action_options, target_type_options = _list_filter_options(db)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_audit_log_item(x) for x in items],
        "summary": summary,
        "filters": {
            "action_options": action_options,
            "target_type_options": target_type_options,
        },
    }


def _apply_audit_filters(
    q: SAQuery,
    *,
    action: str | None,
    target_type: str | None,
    user_name: str | None,
    keyword: str | None,
    start_at: datetime | None,
    end_at: datetime | None,
    ids_only: bool,
    sensitive_only: bool,
) -> SAQuery:
    if action:
        q = q.filter(AuditLog.action == action)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if user_name:
        q = q.filter(AuditLog.user_name.ilike(f"%{user_name.strip()}%"))
    if keyword:
        kw = keyword.strip()
        if kw:
            like_kw = f"%{kw}%"
            q = q.filter(
                or_(
                    AuditLog.user_name.ilike(like_kw),
                    AuditLog.user_role.ilike(like_kw),
                    AuditLog.action.ilike(like_kw),
                    AuditLog.target_type.ilike(like_kw),
                    AuditLog.target_id.ilike(like_kw),
                    AuditLog.detail.ilike(like_kw),
                )
            )
    if start_at:
        q = q.filter(AuditLog.created_at >= start_at)
    if end_at:
        q = q.filter(AuditLog.created_at <= end_at)
    if ids_only:
        q = q.filter(AuditLog.action.like(f"{IDS_ACTION_PREFIX}%"))
    if sensitive_only:
        q = q.filter(AuditLog.action.in_(SENSITIVE_ACTIONS))
    return q


def _build_summary(q: SAQuery) -> dict:
    total = q.count()
    ids_count = q.filter(AuditLog.action.like(f"{IDS_ACTION_PREFIX}%")).count()
    sensitive_count = q.filter(AuditLog.action.in_(SENSITIVE_ACTIONS)).count()

    utc_now = datetime.utcnow()
    today_start = datetime(utc_now.year, utc_now.month, utc_now.day, 0, 0, 0)
    today_count = q.filter(AuditLog.created_at >= today_start).count()

    by_action_rows = (
        q.with_entities(AuditLog.action, func.count(AuditLog.id).label("cnt"))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.action.asc())
        .limit(12)
        .all()
    )
    by_user_rows = (
        q.with_entities(AuditLog.user_name, func.count(AuditLog.id).label("cnt"))
        .group_by(AuditLog.user_name)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.user_name.asc())
        .limit(12)
        .all()
    )
    by_target_rows = (
        q.with_entities(AuditLog.target_type, func.count(AuditLog.id).label("cnt"))
        .group_by(AuditLog.target_type)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.target_type.asc())
        .limit(12)
        .all()
    )
    return {
        "total": total,
        "ids_count": ids_count,
        "sensitive_count": sensitive_count,
        "today_count": today_count,
        "by_action": [{"name": (name or "-"), "count": int(cnt or 0)} for name, cnt in by_action_rows],
        "by_user": [{"name": (name or "-"), "count": int(cnt or 0)} for name, cnt in by_user_rows],
        "by_target_type": [{"name": (name or "-"), "count": int(cnt or 0)} for name, cnt in by_target_rows],
    }


def _list_filter_options(db: Session) -> tuple[list[str], list[str]]:
    action_rows = (
        db.query(AuditLog.action)
        .filter(AuditLog.action.isnot(None))
        .filter(AuditLog.action != "")
        .distinct()
        .order_by(AuditLog.action.asc())
        .limit(200)
        .all()
    )
    target_rows = (
        db.query(AuditLog.target_type)
        .filter(AuditLog.target_type.isnot(None))
        .filter(AuditLog.target_type != "")
        .distinct()
        .order_by(AuditLog.target_type.asc())
        .limit(200)
        .all()
    )
    return (
        [str(row[0]) for row in action_rows if row and row[0]],
        [str(row[0]) for row in target_rows if row and row[0]],
    )


def _serialize_audit_log_item(x: AuditLog) -> dict:
    action = x.action or ""
    return {
        "id": x.id,
        "user_name": x.user_name,
        "user_role": x.user_role,
        "action": action,
        "target_type": x.target_type,
        "target_id": x.target_id,
        "detail": x.detail,
        "is_ids": action.startswith(IDS_ACTION_PREFIX),
        "is_sensitive": action in SENSITIVE_ACTIONS,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }
