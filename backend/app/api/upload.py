"""公开文件上传接口 - 无需登录，供匿名反馈/举报材料提交（渗透测试入口）"""
import uuid
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, UploadFile, File, Request, Depends, HTTPException
from ..models.user import User
from .deps import require_roles

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_admin = require_roles("system_admin")

HIGH_RISK_EXT = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".scr", ".com", ".dll", ".msi"}
MEDIUM_RISK_EXT = {".php", ".jsp", ".asp", ".aspx", ".zip", ".jar", ".vbs", ".js", ".html", ".htm"}


def _risk_for_name(filename: str) -> str:
    suf = Path(filename).suffix.lower()
    if suf in HIGH_RISK_EXT:
        return "high"
    if suf in MEDIUM_RISK_EXT:
        return "medium"
    return "low"


def _client_public_base(request: Request) -> str:
    """反向代理后生成与浏览器一致的站点根 URL，用于返回可访问的 /uploads/ 链接。"""
    xf_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    xf_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    if xf_host:
        host = xf_host.split(",")[0].strip()
        scheme = xf_proto or "http"
        return f"{scheme}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _safe_upload_path(name: str) -> Path | None:
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    p = (UPLOAD_DIR / Path(name).name).resolve()
    try:
        p.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None
    return p


@router.get("/quarantine")
def list_quarantine(request: Request, _: User = Depends(_admin)):
    """管理员查看匿名上传目录中的隔离文件（沙箱封存区），附统计与简易风险分析"""
    base = str(request.base_url).rstrip("/")
    now = datetime.now(timezone.utc)
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week0 = today0 - timedelta(days=7)
    items = []
    total_bytes = 0
    by_ext: dict[str, int] = defaultdict(int)
    daily: dict[str, int] = defaultdict(int)
    high_n = med_n = 0

    if UPLOAD_DIR.exists():
        for f in sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            st = f.stat()
            total_bytes += st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            iso = mtime.isoformat()
            ext = Path(f.name).suffix.lower() or "(无扩展名)"
            by_ext[ext] += 1
            dkey = mtime.strftime("%Y-%m-%d")
            daily[dkey] += 1
            risk = _risk_for_name(f.name)
            if risk == "high":
                high_n += 1
            elif risk == "medium":
                med_n += 1
            items.append({
                "saved_as": f.name,
                "size": st.st_size,
                "modified_at": iso,
                "url": f"{base}/uploads/{f.name}" if base else f"/uploads/{f.name}",
                "risk_level": risk,
                "extension": ext,
            })

    # 最近 14 天每日计数（含 0）
    labels = []
    counts = []
    for i in range(13, -1, -1):
        d = (today0 - timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(d[5:])  # MM-DD
        counts.append(daily.get(d, 0))

    today_count = sum(1 for it in items if it["modified_at"][:10] == today0.strftime("%Y-%m-%d"))
    week_count = sum(1 for it in items if datetime.fromisoformat(it["modified_at"].replace("Z", "+00:00")) >= week0)

    top_ext = sorted(by_ext.items(), key=lambda x: -x[1])[:6]
    insights = []
    if not items:
        insights.append("沙箱当前无封存对象，匿名上传通道处于空闲状态。")
    else:
        insights.append(f"共封存 {len(items)} 个对象，总占用 {total_bytes / 1024 / 1024:.2f} MB。")
        if high_n:
            insights.append(f"检测到 {high_n} 个高风险扩展名对象（可执行/脚本类），建议优先人工研判。")
        if med_n:
            insights.append(f"另有 {med_n} 个中等风险类型（Web/压缩包等），建议在隔离环境内打开。")
        if today_count:
            insights.append(f"今日新增 {today_count} 条封存记录。")
        else:
            insights.append("今日尚无新增封存记录。")

    analysis = {
        "total_bytes": total_bytes,
        "today_count": today_count,
        "week_count": week_count,
        "high_risk_count": high_n,
        "medium_risk_count": med_n,
        "by_extension": [{"ext": k, "count": v} for k, v in top_ext],
        "daily_labels": labels,
        "daily_counts": counts,
        "insights": insights,
        "generated_at": now.isoformat(),
    }

    return {"items": items, "count": len(items), "analysis": analysis}


@router.delete("/quarantine/{filename:path}")
def delete_quarantine_file(filename: str, _: User = Depends(_admin)):
    """管理员删除隔离区中的单个文件（filename 为保存名，需 URL 编码）"""
    p = _safe_upload_path(filename)
    if not p or not p.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    p.unlink()
    return {"ok": True}


@router.post("")
async def public_upload(request: Request, file: UploadFile = File(...)):
    """公开上传：文件正常落盘（功能可用）。响应内附 security_alert，供前端展示「403+木马」演示告警，而非成功 Toast。"""
    safe_name = Path(file.filename or "unnamed").name
    unique = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    dest = UPLOAD_DIR / unique
    content = await file.read()
    dest.write_bytes(content)
    base = _client_public_base(request)
    return {
        "ok": True,
        "filename": safe_name,
        "saved_as": unique,
        "size": len(content),
        "url": f"{base}/uploads/{unique}",
        "security_alert": {
            "style": "simulated_403_malware",
            "http_status_hint": 403,
            "title": "403 Forbidden · 木马 / WebShell 安全告警（演示）",
            "message": (
                "沙箱引擎检测到疑似木马、WebShell 或高风险可执行载荷特征，已触发与 HTTP 403 等效的安全阻断告警。"
                " 文件已写入服务器隔离目录，功能侧上传成功，仅供人工复核与审计（此为演示文案）。"
            ),
            "detail": f"原始文件名：{safe_name}；落盘名：{unique}；大小：{len(content)} 字节",
        },
    }
