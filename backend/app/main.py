from pathlib import Path
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import engine, Base
from .api import auth, goods, ai, purchase, supplier, trace, warning, stock, delivery, dashboard, audit, ids, upload
from .middleware.ids_middleware import IDSMiddleware
from .schema_sync import ensure_schema

# 创建表
Base.metadata.create_all(bind=engine)
ensure_schema(engine)

app = FastAPI(title="校园物资供应链安全监测平台 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(IDSMiddleware)


@app.on_event("startup")
def startup():
    """启动时打印 LLM 配置状态，并确保 system_admin 存在"""
    u = getattr(settings, "LLM_BASE_URL", None)
    p = getattr(settings, "LLM_PROVIDER", "")
    print(f"[启动] LLM: {'已配置' if u else '未配置'} (provider={p}, base={u or '-'})")
    # 确保 system_admin 存在，避免登录 400
    from .database import SessionLocal
    from .models.user import User
    from .core.security import get_password_hash
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "system_admin").first()
        if not admin:
            legacy = db.query(User).filter(User.username == "admin").first()
            if legacy:
                legacy.role = "system_admin"
                legacy.real_name = legacy.real_name or "管理员"
            else:
                db.add(User(
                    username="system_admin",
                    hashed_password=get_password_hash("123456"),
                    real_name="管理员",
                    role="system_admin",
                ))
            db.commit()
            print("[启动] 已创建/更新 system_admin 账号（密码 123456）")
    finally:
        db.close()

# 健康检查等系统路由（优先注册，避免被其他路由覆盖）
_health_router = APIRouter(tags=["system"])
@_health_router.get("/health")
def api_health():
    return {"status": "ok", "llm_configured": bool(settings.LLM_BASE_URL), "llm_provider": settings.LLM_PROVIDER}
app.include_router(_health_router, prefix="/api")

# 所有路由挂在 /api 下，与前端 baseURL 一致
app.include_router(auth.router, prefix="/api")
app.include_router(goods.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(purchase.router, prefix="/api")
app.include_router(supplier.router, prefix="/api")
app.include_router(trace.router, prefix="/api")
app.include_router(warning.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(delivery.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(ids.router, prefix="/api")
app.include_router(upload.router, prefix="/api")

# 静态文件：上传文件访问
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/")
def root():
    return {"message": "Campus Supply Chain API", "docs": "/docs"}


@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)
