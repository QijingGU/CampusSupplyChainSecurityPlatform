"""真智能体：工具调用 + ReAct 循环 + 多轮对话 + 角色分流"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.goods import Goods
from ..models.stock import Inventory
from ..models.purchase import Purchase, PurchaseItem
from ..models.delivery import Delivery
from ..models.warning import Warning
from ..models.supplier import Supplier
from ..models.audit_log import AuditLog
from ..models.trace import TraceRecord
from ..models.user import User
from ..utils.llm_client import chat_with_tools
from ..config import settings
from .flow import make_flow_code
from .audit import write_audit_log

# 工具定义（OpenAI/DeepSeek Function Calling 格式）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_inventory",
            "description": "查询物资库存。返回各物资的名称、数量、单位、批次。用于分析短缺、补货建议时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "可选，物资名称关键词，留空则返回全部",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_goods_catalog",
            "description": "查询物资目录。返回可供采购的物资名单（名称、单位、规格等）。生成采购建议时必须从此目录选取，物资名需完全一致。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "可选，分类筛选如：食材、茶歇、防疫、办公",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_active_warnings",
            "description": "查询当前未处理预警（pending）。用于回答有哪些风险、异常和待处理事项。",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "description": "可选，按等级过滤：high/medium/low",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_low_stock_warnings",
            "description": "根据库存和安全线自动生成低库存预警。用于主动感知并给出补货决策依据。",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_approval_status",
            "description": "查询当前用户发起的采购申请状态（待审批、已通过、已完成、已驳回）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "可选，返回条数，默认5，最大20",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_status",
            "description": "查询配送状态。可按 delivery_no 过滤，也可返回最近配送单状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_no": {
                        "type": "string",
                        "description": "可选，配送单号",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_past_activities",
            "description": "查询历史类似活动的采购记录，作为参考。传入关键词如：茶歇、班会、讲座、团建、午餐等，返回过去类似活动的采购物资及典型数量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "关键词，如：茶歇、班会、讲座",
                    },
                },
                "required": ["keywords"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_user_options",
            "description": "向用户展示可点击的快捷选项（减少手动输入）。仅用于提问补全信息，不执行采购。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要询问用户的问题"},
                    "options": {
                        "type": "array",
                        "description": "候选项",
                        "items": {"type": "string"},
                    },
                },
                "required": ["question", "options"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_purchase",
            "description": "生成拟申请清单供用户确认。当首次给出采购建议时调用，不直接创建。参数为采购明细。用户确认后再调用 create_purchase。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "拟采购明细",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                            },
                            "required": ["name", "quantity", "unit"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_audit_logs",
            "description": "查询审计日志。用于管理员审查操作留痕、反腐分析。可按动作类型、目标类型筛选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "可选，动作类型如 purchase_reject, supplier_confirm, warning_handle"},
                    "target_type": {"type": "string", "description": "可选，目标类型"},
                    "limit": {"type": "number", "description": "返回条数，默认20"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_supplier_performance",
            "description": "查询供应商履约表现。返回各供应商的订单数、完成率、逾期/异常情况。用于管理员评估供应商、反腐决策。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_purchase",
            "description": "创建采购申请并提交。仅当用户明确说「提交」「确认」「可以」等表示确认时调用。参数为采购明细。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "采购明细",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "物资名称"},
                                "quantity": {"type": "number", "description": "数量"},
                                "unit": {"type": "string", "description": "单位"},
                            },
                            "required": ["name", "quantity", "unit"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    },
]

def _get_system_prompt(role: str) -> str:
    role = (role or "").strip()
    if role == "system_admin":
        return """你是平台治理与反腐审计助手，为管理员提供审计分析、供应商评估和异常处置建议。

工具说明：
1. query_audit_logs - 查询审计日志，关注 purchase_reject、supplier_confirm、warning_handle 等敏感动作
2. query_supplier_performance - 查询供应商履约数据（订单数、完成率、异常）
3. query_inventory - 查询库存
4. list_active_warnings - 查询未处理预警

工作重点：
- 用户问审计、反腐、异常：优先 query_audit_logs，分析敏感操作并给出审查建议
- 用户问供应商表现、不出货、异常：调用 query_supplier_performance，分析后给出建议（如约谈、扣分、清退）
- 用户问审计报告：汇总近期审计日志，按动作类型分类，标注需关注项
- 回复要简洁、有结论、可操作"""
    if role == "warehouse_procurement":
        return """你是仓储管理与执行效率助手，帮助仓管员优化入库、出库和库存管理。

工具说明：
1. query_inventory - 查询库存，分析周转与余量
2. query_goods_catalog - 查询物资目录
3. list_active_warnings - 查询低库存等预警
4. generate_low_stock_warnings - 生成补货预警

工作重点：
- 用户问短缺、补货：先 generate_low_stock_warnings，再给出补货建议
- 用户问入库/出库效率：结合 query_inventory 分析周转，给出批次管理建议
- 用户问管理建议：基于库存数据给出先进先出、临期优先出库等建议
- 回复要实用、可执行"""
    # 默认：采购/教师
    return """你是校园物资供应链智能助手，支持多轮对话，帮助用户明确需求并生成采购申请。

工具说明：
1. query_inventory - 查询库存
2. query_goods_catalog - 查询物资目录（物资名须与目录完全一致）
3. list_active_warnings - 查询未处理预警
4. generate_low_stock_warnings - 生成低库存预警
5. get_my_approval_status - 查询我的申请状态
6. get_delivery_status - 查询配送状态
7. query_past_activities - 查询历史类似活动的采购记录，作为参考
8. suggest_user_options - 给用户展示可点击快捷选项，减少手动输入
9. propose_purchase - 首次生成拟申请清单，供用户确认（不直接提交）
10. create_purchase - 用户确认后再调用，真正提交申请

工作流程：
- 用户描述需求（如40人班会茶歇）→ 调用 query_goods_catalog、query_inventory、query_past_activities 获取参考
- 若信息不足（人数不明、时长不明、是否需要热水等）→ 主动向用户提问，并优先调用 suggest_user_options 提供可点击选项
- 用户回答后，结合数据生成清单 → 调用 propose_purchase 生成拟申请表单
- 明确列出每项物资、数量、计算依据，并询问：「请确认上述清单是否符合需求？如需调整请说明，确认无误请回复「提交」或「确认」」
- 仅当用户明确说「提交」「确认」「可以」等时，才调用 create_purchase

要求：
- 对常见问题（我的申请到哪了/配送到哪了/现在有哪些预警）优先调用 get_my_approval_status/get_delivery_status/list_active_warnings
- 用户问短缺风险时，可先调用 generate_low_stock_warnings，再调用 list_active_warnings
- 多轮对话中引用前文，保持上下文连贯
- 物资名必须与 query_goods_catalog 完全一致
- 数量按「人数×人均用量」计算并写明依据
"""


def process_chat_admin(db: Session, message: str, history: list | None = None) -> dict | None:
    """管理员专用：审计与反腐分析"""
    if settings.LLM_BASE_URL and settings.LLM_PROVIDER in ("deepseek", "openai"):
        return process_chat_agent(db, message, None, history, user_role="system_admin")
    # 无 LLM 时规则响应
    ctx = _build_admin_context(db)
    return {"reply": f"{ctx}\n\n当前未配置大模型，审计与供应商分析需配置 LLM 后使用。", "react": [], "actions": []}


def process_chat_warehouse(db: Session, message: str, history: list | None = None) -> dict | None:
    """仓管专用：仓储效率"""
    if settings.LLM_BASE_URL and settings.LLM_PROVIDER in ("deepseek", "openai"):
        return process_chat_agent(db, message, None, history, user_role="warehouse_procurement")
    # 无 LLM 时给基础建议
    return {"reply": "当前未配置大模型。你可先试试：「现在什么物资可能短缺？」（规则引擎可回答）", "react": [], "actions": []}


def _build_admin_context(db: Session) -> str:
    """管理员上下文"""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    lines = [f"• {l.action} | {l.user_name} | {l.detail[:50]}..." for l in logs[:5]]
    return "【近期审计】\n" + "\n".join(lines) if lines else "【近期审计】暂无"


def _run_tool(db: Session, name: str, args: dict, applicant_id: int | None, out_actions: list | None = None) -> str:
    if name == "query_audit_logs":
        q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
        if args.get("action"):
            q = q.filter(AuditLog.action == args["action"])
        if args.get("target_type"):
            q = q.filter(AuditLog.target_type == args["target_type"])
        limit = min(50, int(args.get("limit") or 20))
        rows = q.limit(limit).all()
        data = [{"action": r.action, "user_name": r.user_name, "user_role": r.user_role, "target_type": r.target_type, "target_id": r.target_id, "detail": r.detail, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
        return json.dumps(data, ensure_ascii=False)

    if name == "query_supplier_performance":
        suppliers = db.query(Supplier).all()
        result = []
        for s in suppliers:
            purchases = db.query(Purchase).filter(Purchase.supplier_id == s.id).all()
            total = len(purchases)
            completed = sum(1 for p in purchases if p.status == "completed")
            rejected = sum(1 for p in purchases if p.status == "rejected")
            pending = sum(1 for p in purchases if p.status in ("pending", "approved", "confirmed", "shipped", "stocked_in", "stocked_out", "delivering"))
            result.append({
                "name": s.name,
                "total_orders": total,
                "completed": completed,
                "rejected": rejected,
                "pending": pending,
                "rate": f"{(completed/total*100):.0f}%" if total else "0%",
            })
        return json.dumps(result, ensure_ascii=False)

    """执行工具，返回字符串结果。propose_purchase 会将 items 写入 out_actions"""
    if name == "query_inventory":
        q = db.query(Inventory)
        if args.get("keyword"):
            q = q.filter(Inventory.goods_name.contains(args["keyword"]))
        rows = q.all()
        data = [{"goods_name": r.goods_name, "quantity": r.quantity, "unit": r.unit or "件", "batch_no": r.batch_no or ""} for r in rows]
        return json.dumps(data, ensure_ascii=False)

    if name == "query_goods_catalog":
        q = db.query(Goods).filter(Goods.is_active == True)
        if args.get("category"):
            q = q.filter(Goods.category.contains(args["category"]))
        rows = q.limit(50).all()
        data = [{"name": r.name, "unit": r.unit or "件", "category": r.category, "spec": r.spec or ""} for r in rows]
        return json.dumps(data, ensure_ascii=False)

    if name == "list_active_warnings":
        q = db.query(Warning).filter(Warning.status == "pending")
        if args.get("level"):
            q = q.filter(Warning.level == args["level"])
        rows = q.order_by(Warning.created_at.desc()).limit(50).all()
        data = [{"id": r.id, "level": r.level, "material": r.material, "description": r.description} for r in rows]
        return json.dumps(data, ensure_ascii=False)

    if name == "generate_low_stock_warnings":
        goods_rows = db.query(Goods).filter(Goods.is_active == True).all()
        goods_by_name = {g.name: g for g in goods_rows}
        inv_rows = db.query(Inventory).all()
        created = 0
        for inv in inv_rows:
            g = goods_by_name.get(inv.goods_name)
            safety_level = (g.safety_level if g else "medium") or "medium"
            safe_qty = 20 if safety_level in ("critical", "high") else 10
            if inv.quantity < safe_qty:
                material = f"{inv.goods_name}"
                exists = db.query(Warning).filter(Warning.status == "pending", Warning.material == material).first()
                if not exists:
                    level = "high" if inv.quantity <= max(2, safe_qty * 0.3) else "medium"
                    db.add(Warning(
                        level=level,
                        material=material,
                        description=f"库存仅 {inv.quantity}{inv.unit or '件'}，低于安全线 {safe_qty}{inv.unit or '件'}，建议补货",
                        status="pending",
                    ))
                    created += 1
        db.commit()
        return json.dumps({"success": True, "created": created}, ensure_ascii=False)

    if name == "get_my_approval_status":
        limit = int(args.get("limit") or 5)
        limit = max(1, min(20, limit))
        q = db.query(Purchase).order_by(Purchase.created_at.desc())
        if applicant_id:
            q = q.filter(Purchase.applicant_id == applicant_id)
        rows = q.limit(limit).all()
        data = []
        for p in rows:
            data.append({
                "order_no": p.order_no,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "items": [{"goods_name": it.goods_name, "quantity": it.quantity, "unit": it.unit} for it in p.items],
            })
        return json.dumps(data, ensure_ascii=False)

    if name == "get_delivery_status":
        q = db.query(Delivery).order_by(Delivery.created_at.desc())
        no = (args.get("delivery_no") or "").strip()
        if no:
            q = q.filter(Delivery.delivery_no == no)
        rows = q.limit(20).all()
        data = [{
            "delivery_no": d.delivery_no,
            "destination": d.destination,
            "status": d.status,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "actual_at": d.actual_at.isoformat() if d.actual_at else None,
            "receiver_name": d.receiver_name or "",
        } for d in rows]
        return json.dumps(data, ensure_ascii=False)

    if name == "query_past_activities":
        kw = (args.get("keywords") or "").strip()
        if not kw:
            return json.dumps([], ensure_ascii=False)
        q = db.query(Purchase).filter(Purchase.status.in_(("completed", "pending", "approved", "confirmed", "shipped", "stocked_in", "stocked_out", "delivering")))
        rows = q.order_by(Purchase.created_at.desc()).limit(30).all()
        result = []
        seen_purchase = set()
        for p in rows:
            items = db.query(PurchaseItem).filter(PurchaseItem.purchase_id == p.id).all()
            has_match = any(kw in it.goods_name for it in items)
            if has_match and p.id not in seen_purchase:
                seen_purchase.add(p.id)
                for it in items:
                    result.append({"order_no": p.order_no, "goods_name": it.goods_name, "quantity": it.quantity, "unit": it.unit})
        return json.dumps(result[:25], ensure_ascii=False)

    if name == "suggest_user_options":
        question = (args.get("question") or "").strip()
        options = [str(x).strip() for x in (args.get("options") or []) if str(x).strip()]
        if out_actions is not None:
            for text in options[:8]:
                out_actions.append({"type": "quick_reply", "label": text, "payload": {"text": text}})
        return json.dumps({"success": True, "question": question, "options": options[:8]}, ensure_ascii=False)

    if name == "propose_purchase":
        items = args.get("items") or []
        if out_actions is not None:
            out_actions.append({"type": "create_purchase", "payload": {"items": items}})
        return json.dumps({"success": True, "message": "已生成拟申请清单，请用户确认后提交"}, ensure_ascii=False)

    if name == "create_purchase":
        items = args.get("items") or []
        if not items:
            return json.dumps({"success": False, "error": "采购明细不能为空"}, ensure_ascii=False)
        order_no = f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"
        purchase = Purchase(
            order_no=order_no,
            status="pending",
            applicant_id=applicant_id,
            handoff_code=make_flow_code("HDP"),
        )
        db.add(purchase)
        db.flush()
        for it in items:
            db.add(PurchaseItem(
                purchase_id=purchase.id,
                goods_name=str(it.get("name", "")),
                quantity=float(it.get("quantity", 0)),
                unit=str(it.get("unit", "")),
            ))
        user = db.query(User).filter(User.id == applicant_id).first() if applicant_id else None
        db.add(
            TraceRecord(
                batch_no=order_no,
                stage="申请",
                content=f"AI 助手提交采购申请；申请人={(user.real_name or user.username) if user else '-'}；交接码={purchase.handoff_code}",
            )
        )
        write_audit_log(
            db,
            user_id=(user.id if user else applicant_id),
            user_name=(user.real_name or user.username) if user else "AI助手",
            user_role=(user.role if user else ""),
            action="purchase_create",
            target_type="purchase",
            target_id=str(purchase.id),
            detail=f"AI 助手创建采购申请 {order_no}，交接码={purchase.handoff_code}",
        )
        db.commit()
        return json.dumps({"success": True, "order_no": order_no, "message": "采购申请已创建，等待管理员审批"}, ensure_ascii=False)

    return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)


def process_chat_agent(db: Session, message: str, applicant_id: int | None = None, history: list | None = None, user_role: str = "") -> dict:
    """
    真智能体：工具调用循环，支持多轮对话。
    history: [{"role":"user"|"assistant","content":"..."}, ...] 按时间顺序
    返回 { reply, react, actions, trace }
    """
    system_prompt = _get_system_prompt(user_role)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for h in history[-16:]:  # 最多8轮
            r = h.get("role")
            c = h.get("content") or ""
            if r in ("user", "assistant") and c:
                messages.append({"role": r, "content": c})
    messages.append({"role": "user", "content": message})

    out_actions = []
    react_steps = []
    trace_result = None
    max_turns = 8
    turn = 0

    while turn < max_turns:
        turn += 1
        content, tool_calls = chat_with_tools(messages, TOOLS)

        if not tool_calls:
            # 无工具调用，为最终回复
            final_reply = content or "抱歉，我暂时无法回答。请稍后重试或换个方式描述。"
            acts = []
            for a in out_actions:
                if a.get("type") == "quick_reply":
                    acts.append({
                        "type": "quick_reply",
                        "label": a.get("label", "快捷选项"),
                        "payload": a.get("payload", {}),
                    })
                else:
                    acts.append({
                        "type": a.get("type", "create_purchase"),
                        "label": a.get("label", "确认提交"),
                        "payload": a.get("payload", {}),
                    })
            return {
                "reply": final_reply,
                "react": react_steps,
                "actions": acts,
                "trace": trace_result,
            }

        # 有工具调用：1) 添加 assistant 消息（含全部 tool_calls） 2) 逐个执行并添加 tool 结果
        assistant_msg = {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {"name": tc.get("name", ""), "arguments": json.dumps(tc.get("arguments") or {}, ensure_ascii=False)},
                }
                for tc in tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("arguments") or {}
            react_steps.append({"step": len(react_steps) + 1, "text": f"调用工具: {name}"})
            result = _run_tool(db, name, args, applicant_id, out_actions)
            if name == "create_purchase":
                try:
                    tr = json.loads(result)
                    if tr.get("success"):
                        trace_result = {
                            "orderNo": tr.get("order_no", ""),
                            "executedAt": datetime.now().isoformat(),
                            "action": "create_purchase",
                        }
                except Exception:
                    pass

            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})

    # 超过轮次，返回当前内容
    acts = []
    for a in out_actions:
        if a.get("type") == "quick_reply":
            acts.append({
                "type": "quick_reply",
                "label": a.get("label", "快捷选项"),
                "payload": a.get("payload", {}),
            })
        else:
            acts.append({
                "type": a.get("type", "create_purchase"),
                "label": a.get("label", "确认提交"),
                "payload": a.get("payload", {}),
            })
    return {
        "reply": content or "处理超时，请简化问题后重试。",
        "react": react_steps,
        "actions": acts,
        "trace": trace_result,
    }
