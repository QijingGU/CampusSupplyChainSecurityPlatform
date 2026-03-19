"""初始化数据库并插入演示数据"""
import sys
sys.path.insert(0, ".")

from datetime import datetime
from app.database import SessionLocal, engine, Base
from app.schema_sync import ensure_schema
from app.models import User, Goods, Supplier, Purchase, PurchaseItem, TraceRecord, Warning
from app.models.stock import Inventory, StockIn, StockOut
from app.models.delivery import Delivery
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)
ensure_schema(engine)

db = SessionLocal()

# 演示用户（密码均为 123456）
DEMO_USERS = [
    {"username": "system_admin", "real_name": "管理员", "role": "system_admin"},
    {"username": "logistics_admin", "real_name": "后勤管理员", "role": "logistics_admin"},
    {"username": "warehouse_procurement", "real_name": "仓储采购员", "role": "warehouse_procurement"},
    {"username": "campus_supplier", "real_name": "校园合作供应商", "role": "campus_supplier"},
    {"username": "counselor_teacher", "real_name": "辅导员教师", "role": "counselor_teacher"},
]

for u in DEMO_USERS:
    user = db.query(User).filter(User.username == u["username"]).first()
    if not user:
        user = User(
            username=u["username"],
            hashed_password=get_password_hash("123456"),
            real_name=u["real_name"],
            role=u["role"],
        )
        db.add(user)
    else:
        user.real_name = u["real_name"]
        user.role = u["role"]

# 兼容迁移：老角色 -> 新角色（避免旧数据库权限错乱）
old_to_new_role = {
    "admin": "system_admin",
    "procurement": "warehouse_procurement",
    "supplier": "campus_supplier",
    "teacher": "counselor_teacher",
}
for u in db.query(User).all():
    if u.role in old_to_new_role:
        u.role = old_to_new_role[u.role]

# 演示物资（含班会茶歇常用）
DEMO_GOODS = [
    {"name": "大米", "category": "食材", "spec": "25kg/袋", "unit": "袋", "safety_level": "high", "shelf_life_days": 180},
    {"name": "食用油", "category": "食材", "spec": "5L/桶", "unit": "桶", "safety_level": "high", "shelf_life_days": 365},
    {"name": "面粉", "category": "食材", "spec": "25kg/袋", "unit": "袋", "safety_level": "medium", "shelf_life_days": 180},
    {"name": "口罩", "category": "防疫", "spec": "50只/盒", "unit": "盒", "safety_level": "medium", "shelf_life_days": 365},
    {"name": "矿泉水", "category": "饮品", "spec": "550ml/瓶", "unit": "瓶", "safety_level": "medium", "shelf_life_days": 365},
    {"name": "小零食", "category": "茶歇", "spec": "独立包装", "unit": "份", "safety_level": "medium", "shelf_life_days": 90},
    {"name": "纸巾", "category": "茶歇", "spec": "抽纸", "unit": "盒", "safety_level": "low", "shelf_life_days": 365},
    {"name": "茶包", "category": "茶歇", "spec": "红茶/绿茶", "unit": "盒", "safety_level": "low", "shelf_life_days": 365},
    # 比赛场景（纸质/信息/答辩/实操）
    {"name": "A4打印纸", "category": "办公", "spec": "500张/包", "unit": "包", "safety_level": "medium", "shelf_life_days": 3650},
    {"name": "签字笔", "category": "办公", "spec": "黑色中性笔", "unit": "支", "safety_level": "medium", "shelf_life_days": 3650},
    {"name": "2B铅笔", "category": "办公", "spec": "考试专用", "unit": "支", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "橡皮", "category": "办公", "spec": "学生橡皮", "unit": "块", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "插线板", "category": "设备", "spec": "6位", "unit": "个", "safety_level": "high", "shelf_life_days": 3650},
    {"name": "网线", "category": "设备", "spec": "5米", "unit": "根", "safety_level": "medium", "shelf_life_days": 3650},
    {"name": "备用鼠标", "category": "设备", "spec": "USB有线", "unit": "个", "safety_level": "medium", "shelf_life_days": 3650},
    {"name": "备用键盘", "category": "设备", "spec": "USB有线", "unit": "个", "safety_level": "medium", "shelf_life_days": 3650},
    {"name": "激光笔", "category": "设备", "spec": "翻页激光笔", "unit": "支", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "5号电池", "category": "设备", "spec": "碱性电池", "unit": "节", "safety_level": "medium", "shelf_life_days": 1825},
    {"name": "计时器", "category": "设备", "spec": "电子计时器", "unit": "个", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "绝缘胶带", "category": "设备", "spec": "电工胶带", "unit": "卷", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "扎带", "category": "设备", "spec": "尼龙扎带", "unit": "包", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "螺丝刀套装", "category": "设备", "spec": "多功能", "unit": "套", "safety_level": "low", "shelf_life_days": 3650},
    {"name": "备用电池包", "category": "设备", "spec": "锂电池组", "unit": "包", "safety_level": "medium", "shelf_life_days": 1825},
]
for g in DEMO_GOODS:
    if not db.query(Goods).filter(Goods.name == g["name"]).first():
        db.add(Goods(**g))

# 演示供应商
for name in ["XX食品有限公司", "YY粮油公司"]:
    if not db.query(Supplier).filter(Supplier.name == name).first():
        db.add(Supplier(name=name, contact="负责人", phone="13800138000"))
db.flush()

# 供应商账号绑定公司，确保 supplier1 能看到“我的订单”
supplier_user = db.query(User).filter(User.username.in_(["campus_supplier", "supplier1"])).order_by(User.id.asc()).first()
supplier_company = db.query(Supplier).filter(Supplier.name == "XX食品有限公司").first()
if supplier_user and supplier_company and supplier_user.supplier_id != supplier_company.id:
    supplier_user.supplier_id = supplier_company.id

# 演示溯源（批次号 BATCH2024001）
if not db.query(TraceRecord).first():
    for stage, content in [
        ("供应商", "XX食品有限公司"),
        ("采购", "采购单 PO20240301001"),
        ("入库", "入库单 IN20240308001"),
        ("仓储", "仓位 A-01"),
        ("配送", "食堂A 已签收"),
    ]:
        db.add(TraceRecord(batch_no="BATCH2024001", stage=stage, content=content))

# 演示库存（供智能体短缺分析）- 按物资补齐，避免已有库存时不插入
demo_inventory = [
    ("大米", "食材", 8, "袋"),
    ("食用油", "食材", 12, "桶"),
    ("面粉", "食材", 25, "袋"),
    ("矿泉水", "饮品", 26, "瓶"),
    ("小零食", "茶歇", 18, "份"),
    ("纸巾", "茶歇", 3, "盒"),
    ("茶包", "茶歇", 2, "盒"),
    ("A4打印纸", "办公", 6, "包"),
    ("签字笔", "办公", 80, "支"),
    ("2B铅笔", "办公", 100, "支"),
    ("橡皮", "办公", 40, "块"),
    ("插线板", "设备", 4, "个"),
    ("网线", "设备", 6, "根"),
    ("备用鼠标", "设备", 3, "个"),
    ("备用键盘", "设备", 2, "个"),
    ("激光笔", "设备", 2, "支"),
    ("5号电池", "设备", 20, "节"),
    ("计时器", "设备", 2, "个"),
    ("绝缘胶带", "设备", 3, "卷"),
    ("扎带", "设备", 4, "包"),
    ("螺丝刀套装", "设备", 2, "套"),
    ("备用电池包", "设备", 3, "包"),
]
for inv in demo_inventory:
    exists = db.query(Inventory).filter(Inventory.goods_name == inv[0]).first()
    if not exists:
        db.add(Inventory(goods_name=inv[0], category=inv[1], quantity=inv[2], unit=inv[3]))

# 演示采购历史（支持 query_past_activities、多环节状态演示）
admin = db.query(User).filter(User.username.in_(["logistics_admin", "system_admin", "admin"])).order_by(User.id.asc()).first()
teacher = db.query(User).filter(User.username.in_(["counselor_teacher", "teacher1"])).order_by(User.id.asc()).first()
supplier_a = db.query(Supplier).filter(Supplier.name == "XX食品有限公司").first()
if teacher and admin and supplier_a:
    demo_pos = [
        {
            "order_no": "PO202603100001",
            "status": "completed",
            "items": [("矿泉水", 40, "瓶"), ("小零食", 40, "份"), ("纸巾", 2, "盒")],
            "destination": "图书馆报告厅",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDR202603100001",
        },
        {
            "order_no": "PO202603110001",
            "status": "approved",
            "items": [("矿泉水", 60, "瓶"), ("小零食", 60, "份"), ("茶包", 2, "盒")],
            "destination": "302实验室",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDA202603110001",
        },
        {
            "order_no": "PO202603120001",
            "status": "pending",
            "items": [("纸巾", 6, "盒"), ("茶包", 3, "盒")],
            "destination": "行政楼会议室",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDP202603120001",
        },
        {
            "order_no": "PO202603130001",
            "status": "confirmed",
            "items": [("A4打印纸", 8, "包"), ("签字笔", 30, "支")],
            "destination": "实训楼A101",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDS202603130001",
        },
        {
            "order_no": "PO202603140001",
            "status": "stocked_in",
            "items": [("插线板", 4, "个"), ("网线", 8, "根")],
            "destination": "机房B203",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDI202603140001",
        },
        {
            "order_no": "PO202603150001",
            "status": "stocked_out",
            "items": [("矿泉水", 30, "瓶"), ("纸巾", 3, "盒")],
            "destination": "体育馆备赛区",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDO202603150001",
        },
        {
            "order_no": "PO202603160001",
            "status": "delivering",
            "items": [("备用鼠标", 4, "个"), ("备用键盘", 2, "个")],
            "destination": "信息楼机房",
            "receiver_name": "辅导员教师",
            "handoff_code": "HDD202603160001",
        },
    ]
    for d in demo_pos:
        p = db.query(Purchase).filter(Purchase.order_no == d["order_no"]).first()
        if not p:
            p = Purchase(
                order_no=d["order_no"],
                status=d["status"],
                applicant_id=teacher.id,
                supplier_id=supplier_a.id if d["status"] in ("approved", "confirmed", "stocked_in", "stocked_out", "delivering", "completed") else None,
                approved_by_id=admin.id if d["status"] in ("approved", "confirmed", "stocked_in", "stocked_out", "delivering", "completed") else None,
                destination=d["destination"],
                receiver_name=d["receiver_name"],
                handoff_code=d["handoff_code"],
            )
            db.add(p)
            db.flush()
            for name, qty, unit in d["items"]:
                db.add(PurchaseItem(purchase_id=p.id, goods_name=name, quantity=qty, unit=unit))
        if not db.query(TraceRecord).filter(TraceRecord.batch_no == d["order_no"]).first():
            db.add(TraceRecord(batch_no=d["order_no"], stage="申请", content=f"申请已创建；收货人={d['receiver_name']}；地点={d['destination']}；交接码={d['handoff_code']}"))
            if d["status"] in ("approved", "confirmed", "stocked_in", "stocked_out", "delivering", "completed"):
                db.add(TraceRecord(batch_no=d["order_no"], stage="审批", content=f"后勤审批通过；交接码={d['handoff_code']}"))
            if d["status"] in ("confirmed", "stocked_in", "stocked_out", "delivering", "completed"):
                db.add(TraceRecord(batch_no=d["order_no"], stage="供应商", content=f"供应商已接单；交接码={d['handoff_code']}"))
            if d["status"] in ("stocked_in", "stocked_out", "delivering", "completed"):
                db.add(TraceRecord(batch_no=d["order_no"], stage="入库", content=f"仓储已入库；交接码={d['handoff_code']}"))
            if d["status"] in ("stocked_out", "delivering", "completed"):
                db.add(TraceRecord(batch_no=d["order_no"], stage="出库", content=f"仓储按申请出库；交接码={d['handoff_code']}"))
            if d["status"] in ("delivering", "completed"):
                db.add(TraceRecord(batch_no=d["order_no"], stage="配送", content=f"配送执行中；交接码={d['handoff_code']}"))
            if d["status"] == "completed":
                db.add(TraceRecord(batch_no=d["order_no"], stage="签收", content=f"教师已确认收货；闭环完成；交接码={d['handoff_code']}"))

# 演示入库/出库
if not db.query(StockIn).first():
    for x in [("IN001", "大米", 50, "袋", "BATCH2024001"), ("IN002", "食用油", 20, "桶", "BATCH2024002")]:
        db.add(StockIn(order_no=x[0], goods_name=x[1], quantity=x[2], unit=x[3], batch_no=x[4]))
if not db.query(StockOut).first():
    db.add(StockOut(order_no="OUT001", goods_name="大米", quantity=10, unit="袋", batch_no="BATCH2024001"))

# 演示配送
if not db.query(Delivery).first():
    db.add(Delivery(delivery_no="DLV001", destination="食堂A", status="received", receiver_name="李老师"))
    db.add(Delivery(delivery_no="DLV002", destination="302实验室", status="on_way", scheduled_at=datetime.now()))
    db.add(Delivery(delivery_no="DLV003", destination="行政楼会议室", status="pending", scheduled_at=datetime.now()))

demo_delivery_purchase = db.query(Purchase).filter(Purchase.order_no == "PO202603160001").first()
if demo_delivery_purchase and not db.query(Delivery).filter(Delivery.purchase_id == demo_delivery_purchase.id).first():
    db.add(
        Delivery(
            delivery_no="DLV202603160001",
            purchase_id=demo_delivery_purchase.id,
            receiver_user_id=teacher.id if teacher else None,
            destination=demo_delivery_purchase.destination or "信息楼机房",
            status="on_way",
            receiver_name=demo_delivery_purchase.receiver_name or "辅导员教师",
            handoff_code=demo_delivery_purchase.handoff_code or "HDD202603160001",
            scheduled_at=datetime.now(),
        )
    )

# 演示预警
if not db.query(Warning).first():
    for w in [
        ("high", "大米 25kg", "库存低于安全线，3 天内可能断货"),
        ("medium", "食用油 5L", "临期 7 天，建议优先使用"),
    ]:
        db.add(Warning(level=w[0], material=w[1], description=w[2]))

db.commit()

print("初始化完成。演示账号：system_admin / logistics_admin / warehouse_procurement / campus_supplier / counselor_teacher，密码：123456")
db.close()
