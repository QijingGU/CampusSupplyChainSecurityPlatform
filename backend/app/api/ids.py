"""IDS 管理 API：管理员查看事件、归档、统计"""
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.ids_event import IDSEvent
from ..api.deps import require_roles

router = APIRouter(prefix="/ids", tags=["ids"])
_admin = require_roles("system_admin")


class ArchiveBatchRequest(BaseModel):
    event_ids: list[int] = []


@router.get("/events")
def list_ids_events(
    attack_type: str | None = Query(None),
    client_ip: str | None = Query(None),
    blocked: int | None = Query(None),
    archived: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    """管理员：查询 IDS 事件列表"""
    q = db.query(IDSEvent).order_by(IDSEvent.created_at.desc())
    if attack_type:
        q = q.filter(IDSEvent.attack_type == attack_type)
    if client_ip:
        q = q.filter(IDSEvent.client_ip.contains(client_ip))
    if blocked is not None:
        q = q.filter(IDSEvent.blocked == blocked)
    if archived is not None:
        q = q.filter(IDSEvent.archived == archived)

    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "client_ip": r.client_ip,
                "attack_type": r.attack_type,
                "attack_type_label": _attack_type_label(r.attack_type),
                "signature_matched": r.signature_matched,
                "method": r.method,
                "path": r.path,
                "query_snippet": (r.query_snippet or "")[:200],
                "body_snippet": (r.body_snippet or "")[:200],
                "user_agent": (r.user_agent or "")[:200],
                "blocked": r.blocked,
                "firewall_rule": r.firewall_rule or "",
                "archived": r.archived,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/stats")
def ids_stats(
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    """管理员：IDS 统计"""
    total = db.query(IDSEvent).count()
    blocked_count = db.query(IDSEvent).filter(IDSEvent.blocked == 1).count()
    by_type = (
        db.query(IDSEvent.attack_type, func.count(IDSEvent.id).label("cnt"))
        .group_by(IDSEvent.attack_type)
        .all()
    )
    return {
        "total": total,
        "blocked_count": blocked_count,
        "by_type": [
            {"attack_type": t, "attack_type_label": _attack_type_label(t), "count": c}
            for t, c in by_type
        ],
    }


@router.get("/stats/trend")
def ids_stats_trend(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    """管理员：IDS 事件时间趋势（按天）"""
    start = datetime.utcnow() - timedelta(days=days)
    rows = db.query(IDSEvent).filter(IDSEvent.created_at >= start).all()
    by_date: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.created_at:
            dt = r.created_at.strftime("%Y-%m-%d")
            by_date[dt] += 1
    dates: list[str] = []
    counts: list[int] = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        dates.append(d)
        counts.append(by_date.get(d, 0))
    return {"dates": dates, "counts": counts}


@router.put("/events/{event_id}/archive")
def archive_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    """管理员：归档单条事件"""
    evt = db.query(IDSEvent).filter(IDSEvent.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="事件不存在")
    evt.archived = 1
    db.commit()
    return {"code": 200, "message": "已归档"}


@router.post("/events/archive-batch")
def archive_batch(
    req: ArchiveBatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(_admin),
):
    """管理员：批量归档"""
    event_ids = req.event_ids or []
    if not event_ids:
        return {"code": 200, "message": "未选择任何事件", "archived": 0}
    db.query(IDSEvent).filter(IDSEvent.id.in_(event_ids)).update({IDSEvent.archived: 1}, synchronize_session=False)
    db.commit()
    return {"code": 200, "message": f"已归档 {len(event_ids)} 条", "archived": len(event_ids)}


def _attack_type_label(t: str) -> str:
    labels = {
        "sql_injection": "SQL 注入",
        "xss": "跨站脚本 XSS",
        "path_traversal": "路径遍历",
        "cmd_injection": "命令注入",
        "scanner": "扫描器/探测",
        "malformed": "畸形请求",
    }
    return labels.get(t or "", t or "-")
