from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.purchase import Purchase, PurchaseItem
from ..models.goods import Goods
from ..models.stock import Inventory
from ..models.supplier import Supplier
from ..models.trace import TraceRecord
from ..models.delivery import Delivery
from ..models.user import User
from ..api.deps import get_current_user, require_roles
from ..services.audit import write_audit_log
from ..services.flow import append_trace, get_delivery_status_label, get_purchase_status_label, make_flow_code
from ..services.workflow import assert_positive, assert_transition

router = APIRouter(prefix="/purchase", tags=["purchase"])
_purchase_reviewer = require_roles("logistics_admin")
_purchase_viewer = require_roles("logistics_admin", "warehouse_procurement")
_purchase_applicant = require_roles("counselor_teacher")


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


@router.post("")
def create_purchase(
    req: PurchaseApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_applicant),
):
    """采购申请：根据物资 ID 创建采购单"""
    assert_positive(req.quantity, "申请数量")
    goods = db.query(Goods).filter(Goods.id == req.goods_id, Goods.is_active == True).first()
    if not goods:
        raise HTTPException(status_code=404, detail="物资不存在")
    order_no = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"
    handoff_code = make_flow_code("HDP")
    purchase = Purchase(
        order_no=order_no,
        status="pending",
        applicant_id=current_user.id,
        destination=(req.destination or "").strip(),
        receiver_name=(req.receiver_name or current_user.real_name or current_user.username or "").strip(),
        handoff_code=handoff_code,
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
        detail=f"创建采购申请 {order_no}，物资={goods.name}，数量={req.quantity}{goods.unit or '件'}，交接码={handoff_code}",
    )
    append_trace(
        db,
        order_no,
        "申请",
        f"申请人 {current_user.real_name or current_user.username} 提交采购申请：{goods.name} {req.quantity}{goods.unit or '件'}；收货人={purchase.receiver_name or '-'}；目的地={purchase.destination or '-'}；交接码={handoff_code}",
    )
    db.commit()
    return {
        "id": purchase.id,
        "order_no": order_no,
        "status": "pending",
        "status_label": get_purchase_status_label("pending"),
        "handoff_code": handoff_code,
        "message": "申请已提交，等待审批",
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
        }
        for p in items
    ]


class ApproveRequest(BaseModel):
    supplier_id: int | None = None


class RejectRequest(BaseModel):
    reason: str = ""


@router.put("/{purchase_id}/approve")
def approve_purchase(
    purchase_id: int,
    req: ApproveRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_reviewer),
):
    """管理员/采购员：审批通过采购单"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")
    assert_transition(p.status, {"pending"}, "审批通过")
    p.approved_by_id = current_user.id
    p.rejected_reason = None
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
    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_approve",
        target_type="purchase",
        target_id=str(p.id),
        detail=f"审批通过采购单 {p.order_no}，分配供应商ID={p.supplier_id or '-'}，路线={route_detail}，交接码={p.handoff_code}",
    )
    append_trace(
        db,
        p.order_no,
        "审批",
        f"审批人 {current_user.real_name or current_user.username} 审批通过；{route_detail}；供应商ID={p.supplier_id or '-'}；当前状态={get_purchase_status_label(p.status)}；交接码={p.handoff_code}",
    )
    db.commit()
    return {"code": 200, "message": route_message, "order_no": p.order_no, "handoff_code": p.handoff_code, "status": p.status}


@router.put("/{purchase_id}/reject")
def reject_purchase(
    purchase_id: int,
    req: RejectRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_purchase_reviewer),
):
    """管理员/采购员：驳回采购单"""
    p = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="采购单不存在")
    assert_transition(p.status, {"pending"}, "驳回")
    p.status = "rejected"
    p.approved_by_id = None
    p.rejected_reason = (req.reason if req else "") or "已驳回"
    write_audit_log(
        db,
        user_id=current_user.id,
        user_name=current_user.real_name or current_user.username,
        user_role=current_user.role,
        action="purchase_reject",
        target_type="purchase",
        target_id=str(p.id),
        detail=f"驳回采购单 {p.order_no}，原因={p.rejected_reason}",
    )
    append_trace(
        db,
        p.order_no,
        "审批",
        f"审批人 {current_user.real_name or current_user.username} 驳回，原因：{p.rejected_reason}",
    )
    db.commit()
    return {"code": 200, "message": "已驳回", "order_no": p.order_no}


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
