"""公开文件上传接口 - 无需登录，供匿名反馈/举报材料提交（渗透测试入口）"""
from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, Request

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("")
async def public_upload(request: Request, file: UploadFile = File(...)):
    """公开上传，无需认证。保存到 uploads/ 目录，保留原始文件名（便于渗透测试）"""
    # 简单防路径穿越：仅取 basename
    safe_name = Path(file.filename or "unnamed").name
    # 可选：加随机前缀避免覆盖
    unique = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    dest = UPLOAD_DIR / unique
    content = await file.read()
    dest.write_bytes(content)
    base = str(request.base_url).rstrip("/")
    return {
        "ok": True,
        "filename": safe_name,
        "saved_as": unique,
        "size": len(content),
        "url": f"{base}/uploads/{unique}",
    }
