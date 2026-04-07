from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import ai, audit, auth, dashboard, delivery, goods, ids, overview, purchase, stock, supplier, trace, upload, warning
from .config import PRIVATE_LAN_CORS_REGEX, settings
from .database import Base, SessionLocal, engine
from .middleware.ids_middleware import IDSMiddleware
from .schema_sync import ensure_schema
from .services.ids_runtime_bootstrap import bootstrap_ids_runtime_source
from .services.llm_startup import ensure_llm_ready_for_ids, llm_runtime_status

Base.metadata.create_all(bind=engine)
ensure_schema(engine)

app = FastAPI(title="Campus Supply Chain Security Platform API", version="1.0.0")

_cors_kw: dict = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.CORS_ALLOW_PRIVATE_NETWORKS:
    _cors_kw["allow_origin_regex"] = PRIVATE_LAN_CORS_REGEX

app.add_middleware(CORSMiddleware, **_cors_kw)
app.add_middleware(IDSMiddleware)


@app.on_event("startup")
def startup() -> None:
    if settings.IDS_AI_ANALYSIS:
        ensure_llm_ready_for_ids()

    runtime_status = bootstrap_ids_runtime_source()
    print(
        "[startup] IDS runtime bootstrap: "
        f"status={runtime_status.get('status')}, "
        f"source={runtime_status.get('source_key')}, "
        f"package={runtime_status.get('package_version') or '-'}, "
        f"rules={runtime_status.get('rule_count')}"
    )

    llm_status = llm_runtime_status()
    print(
        "[startup] Upload audit mode: "
        f"{llm_status['upload_audit_label']} "
        f"(llm_configured={'yes' if llm_status['ready'] else 'no'}, "
        f"provider={llm_status['provider']}, model={llm_status['model']}, "
        f"base={llm_status['effective_base_url'] or '-'})"
    )

    from .core.security import get_password_hash
    from .models.user import User

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "system_admin").first()
        if not admin:
            legacy = db.query(User).filter(User.username == "admin").first()
            if legacy:
                legacy.role = "system_admin"
                legacy.real_name = legacy.real_name or "管理员"
            else:
                db.add(
                    User(
                        username="system_admin",
                        hashed_password=get_password_hash("123456"),
                        real_name="管理员",
                        role="system_admin",
                    )
                )
            db.commit()
            print("[startup] system_admin account is ready (password: 123456)")
    finally:
        db.close()


_health_router = APIRouter(tags=["system"])


@_health_router.get("/health")
def api_health() -> dict:
    llm_status = llm_runtime_status()
    return {
        "status": "ok",
        "ids_ai_analysis_enabled": bool(settings.IDS_AI_ANALYSIS),
        "llm_configured": bool(llm_status["ready"]),
        "llm_provider": llm_status["provider"],
        "llm_model": llm_status["model"],
        "llm_required_field": llm_status["required_field"],
        "llm_base_url": llm_status["effective_base_url"] or None,
        "ids_upload_audit_mode": llm_status["upload_audit_mode"],
        "ids_upload_audit_label": llm_status["upload_audit_label"],
        "ids_upload_audit_message": llm_status["upload_audit_message"],
        "ids_upload_audit_mode_reason": llm_status["upload_audit_mode_reason"],
        "ids_upload_ai_active": bool(llm_status["upload_audit_mode"] == "llm_assisted"),
    }


app.include_router(_health_router, prefix="/api")

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
app.include_router(overview.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(ids.router, prefix="/api")
app.include_router(upload.router, prefix="/api")

_accepted_uploads_dir = Path(__file__).resolve().parent.parent / "uploads" / "accepted"
_accepted_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/accepted", StaticFiles(directory=str(_accepted_uploads_dir)), name="accepted-uploads")


@app.get("/")
def root() -> dict:
    return {"message": "Campus Supply Chain API", "docs": "/docs"}


@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response

    return Response(status_code=204)
