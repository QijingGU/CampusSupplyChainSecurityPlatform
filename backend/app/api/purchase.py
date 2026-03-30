from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.purchase import Purchase, PurchaseItem
from ..models.goods import Goods
from ..models.stock import Inventory
from ..models.supplier import Supplier
from ..models.trace import TraceRecord
from ..models.delivery import Delivery
from ..models.user import User
from ..api.deps import get_current_user, require_roles, has_role, normalize_role
from ..services.audit import write_audit_log
from ..services.flow import append_trace, get_delivery_status_label, get_purchase_status_label, make_flow_code
from ..services.workflow import assert_positive, assert_transition

router = APIRouter(prefix="/purchase", tags=["purchase"])
_purchase_reviewer = require_roles("logistics_admin", "system_admin")
_purchase_viewer = require_roles("logistics_admin", "warehouse_procurement", "system_admin")
_purchase_applicant = require_roles("counselor_teacher")

MATERIAL_TYPES = {"教学", "科研", "办公"}


def _determine_approval(estimated_amount: float, material_type: str, goods_name: str) -> tuple[str, str]:
    """根据金额与类型返回审批级别、审批角色。"""
    goods_name = goods_name or ""
    if material_type == "科研" or "设备" in goods_name or "实验" in goods_name:
        return "special", "system_admin"
    if estimated_amount <= 500:
        return "minor", "logistics_admin"
    if estimated_amount <= 5000:
        return "major", "system_admin"
    return "major", "system_admin"


def _inventory_available_qty(db: Session, goods_name: str) -> float:
    rows = (
        db.query(Inventory)
        .filter(Inventory.goods_name == goods_name, Inventory.quantity > 0)
        .all()
    )
    total = 0.0
    now = datetime.utcnow()
    for row in rows:
        if row.produced_at and row.shelf_life_days:
            expire_at = row.produced_at + timedelta(days=row.shelf_life_days)
            expire_naive = expire_at.replace(tzinfo=None) if getattr(expire_at, "tzinfo", None) else expire_at
            if expire_naive < now:
                continue
        total += float(row.quantity or 0)
    return total


def _can_dispatch_directly(db: Session, purchase: Purchase) -> bool:
    for item in purchase.items:
        if _inventory_available_qty(db, item.goods_name) < float(item.quantity or 0):
            return False
    return True


class PurchaseApplyRequest(BaseModel):
    goods_id: int
    quantity: float
    apply_reason: str = ""
    destination: str = ""
    receiver_name: str = ""
    material_type: str = "教学"
    material_spec: str = ""
    estimated_amount: float = 0
    delivery_date: date | None = None
    attachment_names: list[str] = Field(default_factory=list)
    is_draft: int = 0


@router.post("")
def create_purchase(
    req: PurchaseApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_applicant),
):
    """采购申请：根据物资 ID 创建采购单（支持草稿/交付日期/分级审批）。"""
    assert_positive(req.quantity, "申请数量")
    material_type = (req.material_type or "教学").strip()
    if material_type not in MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail="物资类型仅支持：教学/科研/办公")

    goods = db.query(Goods).filter(Goods.id == req.goods_id, Goods.is_active == True).first()
    if not goods:
        raise HTTPException(status_code=404, detail="物资不存在")

    if req.delivery_date and req.delivery_date < date.today():
        raise HTTPException(status_code=400, detail="交付时间不能早于当前日期")

    estimated_amount = float(req.estimated_amount or 0)
    if estimated_amount < 0:
        raise HTTPException(status_code=400, detail="预估金额不能为负数")

    approval_level, approval_role = _determine_approval(estimated_amount, material_type, goods.name)
    order_no = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"
    handoff_code = make_flow_code("HDP")

    # 紧急程度：48h 内交付视为紧急
    urgent_level = "normal"
    delivery_dt = None
    if req.delivery_date:
        delivery_dt = datetime.combine(req.delivery_date, datetime.min.time())
        if (delivery_dt - datetime.utcnow()).total_seconds() <= 48 * 3600:
            urgent_level = "urgent"

    purchase = Purchase(
        order_no=order_no,
        status="pending" if int(req.is_draft or 0) == 0 else "pending",
        applicant_id=current_user.id,
        destination=(req.destination or "").strip(),
        receiver_name=(req.receiver_name or current_user.real_name or current_user.username or "").strip(),
        handoff_code=handoff_code,
        material_type=material_type,
        material_spec=(req.material_spec or goods.spec or "").strip(),
        estimated_amount=estimated_amount,
        delivery_date=delivery_dt,
        attachment_names=",".join([x.strip() for x in (req.attachment_names or []) if x and x.strip()][:10]),
        is_draft=1 if int(req.is_draft or 0) else 0,
        urgent_level=urgent_level,
        approval_level=approval_level,
        approval_required_role=approval_role,
        approval_deadline_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(purchase)
    db.flush()

    db.add(
        PurchaseItem(
            purchase_id=purchase.id,
            goods_name=goods.name,
            quantity=req.quantity,
            unit=goods.unit or "件",
        )
    )

    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_create",
        target_type="purchase",
        target_id=str(purchase.id),
        detail=(
            f"创建采购申请 {order_no}，物资={goods.name}，数量={req.quantity}{goods.unit or '件'}，"
            f"类型={material_type}，预估金额={estimated_amount:.2f}，审批级别={approval_level}/{approval_role}，交接码={handoff_code}"
        ),
    )

    append_trace(
        db,
        order_no,
        "申请",
        (
            f"申请人 {current_user.real_name or current_user.username} 提交采购申请：{goods.name} {req.quantity}{goods.unit or '件'}；"
            f"类型={material_type}；规格={purchase.material_spec or '-'}；"
            f"交付时间={(delivery_dt.strftime('%Y-%m-%d') if delivery_dt else '-')}；"
            f"审批级别={approval_level}/{approval_role}；交接码={handoff_code}"
        ),
    )
    db.commit()
    return {
        "id": purchase.id,
        "order_no": order_no,
        "status": "pending",
        "status_label": get_purchase_status_label("pending"),
        "handoff_code": handoff_code,
        "approval_level": approval_level,
        "approval_required_role": approval_role,
        "message": "草稿已保存" if purchase.is_draft else "申请已提交，等待审批",
    }


@router.get("/my")
def list_my_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """教师：我的申请（仅本人发起的采购单）"""
    q = db.query(Purchase).filter(Purchase.applicant_id == current_user.id).order_by(Purchase.created_at.desc())
    items = q.limit(50).all()
    deliveries = db.query(Delivery).filter(Delivery.purchase_id.in_([p.id for p in items])).all() if items else []
    delivery_by_purchase: dict[int, list[Delivery]] = {}
    for delivery in deliveries:
        delivery_by_purchase.setdefault(delivery.purchase_id or 0, []).append(delivery)
    return [
        {
            "id": p.id,
            "order_no": p.order_no,
            "status": p.status,
            "status_label": get_purchase_status_label(p.status),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "goods_summary": "、".join(f"{i.goods_name}{i.quantity}{i.unit}" for i in p.items),
            "items": [{"goods_name": i.goods_name, "quantity": i.quantity, "unit": i.unit} for i in p.items],
            "destination": p.destination or "",
            "receiver_name": p.receiver_name or "",
            "handoff_code": p.handoff_code or "",
            "material_type": p.material_type or "",
            "material_spec": p.material_spec or "",
            "estimated_amount": float(p.estimated_amount or 0),
            "delivery_date": p.delivery_date.isoformat() if p.delivery_date else None,
            "attachment_names": [x for x in (p.attachment_names or "").split(",") if x],
            "is_draft": int(p.is_draft or 0),
            "approval_level": p.approval_level or "",
            "approval_required_role": p.approval_required_role or "",
            "approval_deadline_at": p.approval_deadline_at.isoformat() if p.approval_deadline_at else None,
            "urgent_level": p.urgent_level or "normal",
            "delivery_id": (delivery_by_purchase.get(p.id, [])[-1].id if delivery_by_purchase.get(p.id) else None),
            "delivery_no": (delivery_by_purchase.get(p.id, [])[-1].delivery_no if delivery_by_purchase.get(p.id) else ""),
            "delivery_status": (delivery_by_purchase.get(p.id, [])[-1].status if delivery_by_purchase.get(p.id) else ""),
            "delivery_status_label": (
                get_delivery_status_label(delivery_by_purchase.get(p.id, [])[-1].status)
                if delivery_by_purchase.get(p.id)
                else ""
            ),
            "can_confirm_receive": bool(delivery_by_purchase.get(p.id) and delivery_by_purchase.get(p.id)[-1].status == "on_way"),
        }
        for p in items
    ]


@router.get("")
def list_purchases(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_viewer),
):
    """管理员/采购员：查看全部采购单（含待审批）"""
    q = db.query(Purchase).order_by(Purchase.created_at.desc())
    if status:
        q = q.filter(Purchase.status == status)
    items = q.limit(200).all()
    users_by_id = {u.id: u for u in db.query(User).all()}
    return [
        {
            "id": p.id,
            "order_no": p.order_no,
            "status": p.status,
            "status_label": get_purchase_status_label(p.status),
            "applicant_id": p.applicant_id,
            "applicant_name": (u.real_name if (u := users_by_id.get(p.applicant_id)) else None) or "-",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "items": [{"goods_name": i.goods_name, "quantity": i.quantity, "unit": i.unit} for i in p.items],
            "destination": p.destination or "",
            "receiver_name": p.receiver_name or "",
            "handoff_code": p.handoff_code or "",
            "supplier_id": p.supplier_id,
            "material_type": p.material_type or "",
            "material_spec": p.material_spec or "",
            "estimated_amount": float(p.estimated_amount or 0),
            "delivery_date": p.delivery_date.isoformat() if p.delivery_date else None,
            "attachment_names": [x for x in (p.attachment_names or "").split(",") if x],
            "approval_level": p.approval_level or "",
            "approval_required_role": p.approval_required_role or "",
            "approval_deadline_at": p.approval_deadline_at.isoformat() if p.approval_deadline_at else None,
            "urgent_level": p.urgent_level or "normal",
            "forwarded_to": p.forwarded_to or "",
            "forwarded_note": p.forwarded_note or "",
            "is_overdue": bool(p.status == "pending" and p.approval_deadline_at and p.approval_deadline_at.replace(tzinfo=None) < datetime.utcnow()),
        }
        for p in items
    ]


class ApproveRequest(BaseModel):
    supplier_id: int | None = None


class RejectRequest(BaseModel):
    reason: str = ""


class ForwardRequest(BaseModel):
    to_role: str = "system_admin"
    note: str = ""


@router.put("/{purchase_id}/forward")
def forward_purchase(
    purchase_id: int,
    req: ForwardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_viewer),
):
    """协同转发审批：记录转发对象与说明。"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")
    assert_transition(p.status, {"pending"}, "转发协同审批")

    required_role = normalize_role(p.approval_required_role or "logistics_admin")
    if not has_role(current_user, required_role):
        raise HTTPException(status_code=403, detail=f"该单据需由 {required_role} 审批")

    to_role = normalize_role(req.to_role or "system_admin")
    if to_role not in {"logistics_admin", "system_admin"}:
        raise HTTPException(status_code=400, detail="仅支持转发给后勤管理员或系统管理员")

    p.forwarded_to = to_role
    p.forwarded_note = (req.note or "").strip()[:256]
    p.approval_required_role = to_role
    p.approval_deadline_at = datetime.utcnow() + timedelta(hours=24)

    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_forward",
        target_type="purchase",
        target_id=str(p.id),
        detail=f"转发协同审批 {p.order_no}，to_role={to_role}，note={p.forwarded_note or '-'}",
    )
    append_trace(
        db,
        p.order_no,
        "审批",
        f"审批人 {current_user.real_name or current_user.username} 转发协同审批至 {to_role}，备注：{p.forwarded_note or '-'}",
    )
    db.commit()
    return {"code": 200, "message": "已转发协同审批", "order_no": p.order_no, "to_role": to_role}


@router.put("/{purchase_id}/approve")
def approve_purchase(
    purchase_id: int,
    req: ApproveRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_viewer),
):
    """分级审批：金额/类型决定审批人。"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")
    assert_transition(p.status, {"pending"}, "审批通过")

    required_role = normalize_role(p.approval_required_role or "logistics_admin")
    if not has_role(current_user, required_role):
        raise HTTPException(status_code=403, detail=f"该单据需由 {required_role} 审批")

    p.approved_by_id = current_user.id
    p.rejected_reason = None
    p.is_draft = 0
    requested_supplier_id = req.supplier_id if req else None

    if _can_dispatch_directly(db, p):
        p.status = "stocked_in"
        p.supplier_id = None
        p.handoff_code = make_flow_code("HDW")
        route_message = "审批通过，当前库存充足，已直接下发仓储执行出库配送"
        route_detail = "库存充足，转仓储直发"
    else:
        supplier = None
        if requested_supplier_id:
            supplier = db.query(Supplier).filter(Supplier.id == requested_supplier_id, Supplier.is_blacklisted == False).first()
        if not supplier:
            supplier = db.query(Supplier).filter(Supplier.is_blacklisted == False).order_by(Supplier.id.asc()).first()
        if not supplier:
            raise HTTPException(status_code=400, detail="库存不足，且系统未配置可用供应商")
        p.status = "approved"
        p.supplier_id = supplier.id
        p.handoff_code = make_flow_code("HDA")
        route_message = f"审批通过，库存不足，已流转给供应商 {supplier.name} 接单补货"
        route_detail = f"库存不足，已流转供应商 {supplier.name}"

    p.approval_deadline_at = None
    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_approve",
        target_type="purchase",
        target_id=str(p.id),
        detail=(
            f"审批通过采购单 {p.order_no}，审批级别={p.approval_level}/{required_role}，"
            f"分配供应商ID={p.supplier_id or '-'}，路线={route_detail}，交接码={p.handoff_code}"
        ),
    )
    append_trace(
        db,
        p.order_no,
        "审批",
        f"审批人 {current_user.real_name or current_user.username}（{normalize_role(current_user.role)}）审批通过；{route_detail}；供应商ID={p.supplier_id or '-'}；当前状态={get_purchase_status_label(p.status)}；交接码={p.handoff_code}",
    )
    db.commit()
    return {"code": 200, "message": route_message, "order_no": p.order_no, "handoff_code": p.handoff_code, "status": p.status}


@router.put("/{purchase_id}/reject")
def reject_purchase(
    purchase_id: int,
    req: RejectRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_viewer),
):
    """分级审批：驳回采购单。"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")
    assert_transition(p.status, {"pending"}, "驳回")

    required_role = normalize_role(p.approval_required_role or "logistics_admin")
    if not has_role(current_user, required_role):
        raise HTTPException(status_code=403, detail=f"该单据需由 {required_role} 审批")

    p.status = "rejected"
    p.approved_by_id = None
    p.rejected_reason = (req.reason if req else "") or "已驳回"
    p.approval_deadline_at = None
    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_reject",
        target_type="purchase",
        target_id=str(p.id),
        detail=f"驳回采购单 {p.order_no}，审批级别={p.approval_level}/{required_role}，原因={p.rejected_reason}",
    )
    append_trace(
        db,
        p.order_no,
        "审批",
        f"审批人 {current_user.real_name or current_user.username}（{normalize_role(current_user.role)}）驳回，原因：{p.rejected_reason}",
    )
    db.commit()
    return {"code": 200, "message": "已驳回", "order_no": p.order_no}


@router.get("/history")
def list_purchase_history(
    keyword: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_applicant),
):
    """教师历史申请记录。"""
    q = db.query(Purchase).filter(Purchase.applicant_id == current_user.id).order_by(Purchase.created_at.desc())
    if keyword:
        q = q.filter(Purchase.order_no.contains(keyword))
    rows = q.limit(limit).all()
    return [
        {
            "id": p.id,
            "order_no": p.order_no,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "material_type": p.material_type or "",
            "material_spec": p.material_spec or "",
            "estimated_amount": float(p.estimated_amount or 0),
            "delivery_date": p.delivery_date.isoformat() if p.delivery_date else None,
            "goods_summary": "、".join(f"{i.goods_name}{i.quantity}{i.unit}" for i in p.items),
            "status": p.status,
            "status_label": get_purchase_status_label(p.status),
            "is_draft": int(p.is_draft or 0),
        }
        for p in rows
    ]


@router.get("/favorites")
def get_purchase_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_applicant),
):
    """教师常用物资（从近30条申请统计 Top5）。"""
    rows = (
        db.query(Purchase)
        .filter(Purchase.applicant_id == current_user.id)
        .order_by(Purchase.created_at.desc())
        .limit(30)
        .all()
    )
    freq: dict[str, dict] = {}
    for p in rows:
        for item in p.items:
            key = item.goods_name
            cur = freq.get(key) or {
                "goods_name": item.goods_name,
                "quantity": float(item.quantity or 0),
                "unit": item.unit or "件",
                "material_type": p.material_type or "教学",
                "material_spec": p.material_spec or "",
                "estimated_amount": float(p.estimated_amount or 0),
                "count": 0,
            }
            cur["count"] += 1
            freq[key] = cur
    out = sorted(freq.values(), key=lambda x: x["count"], reverse=True)[:5]
    return out


@router.get("/{purchase_id}/timeline")
def get_purchase_timeline(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_viewer),
):
    """单据级闭环时间线：用于展演完整业务链路。"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")

    linked_deliveries = (
        db.query(Delivery)
        .filter(Delivery.purchase_id == p.id)
        .order_by(Delivery.created_at.asc())
        .all()
    )
    delivery_nos = [d.delivery_no for d in linked_deliveries if d.delivery_no]

    # 只拉取“当前采购单”及其“关联配送单号”的追溯，避免串到其它单据
    trace_batches = {p.order_no}
    trace_batches.update([x for x in delivery_nos if x])
    traces = (
        db.query(TraceRecord)
        .filter(TraceRecord.batch_no.in_(list(trace_batches)))
        .order_by(TraceRecord.created_at.asc(), TraceRecord.id.asc())
        .limit(300)
        .all()
    )
    # 向后兼容：历史脏数据若 batch_no 未写规范，则兜底用 content 精确包含单号补齐
    if not traces:
        traces = (
            db.query(TraceRecord)
            .filter(TraceRecord.content.contains(p.order_no))
            .order_by(TraceRecord.created_at.asc(), TraceRecord.id.asc())
            .limit(120)
            .all()
        )

    # 固定阶段顺序，便于展示“成熟闭环”
    stage_order = {
        "申请": 10,
        "审批": 20,
        "供应商": 30,
        "入库": 40,
        "出库": 50,
        "配送": 60,
        "签收": 70,
    }

    timeline = [
        {
            "stage": t.stage,
            "content": t.content,
            "time": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "",
            "_order": stage_order.get(t.stage, 999),
            "_ts": t.created_at or datetime.min,
            "_batch": t.batch_no or "",
        }
        for t in traces
    ]
    # 同时间按阶段排序；先按时间保证“过程可读”，避免看起来阶段乱序/串单
    timeline.sort(key=lambda x: (x["_ts"], x["_order"], x["time"]))
    # 去重：同批次+同阶段+同内容+同时间只保留一条
    deduped: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in timeline:
        key = (item.get("_batch", ""), item.get("stage", ""), item.get("content", ""), item.get("time", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    timeline = deduped
    for item in timeline:
        item.pop("_order", None)
        item.pop("_ts", None)
        item.pop("_batch", None)

    summary = {
        "purchase_id": p.id,
        "order_no": p.order_no,
        "status": p.status,
        "status_label": get_purchase_status_label(p.status),
        "receiver_name": p.receiver_name or "",
        "destination": p.destination or "",
        "handoff_code": p.handoff_code or "",
        "delivery_count": len(linked_deliveries),
        "deliveries": [
            {
                "delivery_no": d.delivery_no,
                "status": d.status,
                "status_label": get_delivery_status_label(d.status),
                "receiver_name": d.receiver_name or "",
                "destination": d.destination or "",
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if d.created_at
                else "",
            }
            for d in linked_deliveries
        ],
    }

    return {"summary": summary, "timeline": timeline}
