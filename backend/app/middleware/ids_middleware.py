"""IDS 中间件：抓包解析 HTTP 请求、特征匹配、识别攻击、留痕、封禁"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from ..database import SessionLocal
from ..models.ids_event import IDSEvent
from ..services.ids_engine import scan_request, block_ip_windows, is_whitelisted

logger = logging.getLogger("ids")


def _get_client_ip(request: Request) -> str:
    for h in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip"):
        v = request.headers.get(h)
        if v:
            return v.split(",")[0].strip()
    if request.client:
        return request.client.host or "0.0.0.0"
    return "0.0.0.0"


class IDSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = _get_client_ip(request)
        path = request.url.path
        if is_whitelisted(path):
            return await call_next(request)

        method = request.method
        query = str(request.query_params)
        headers = dict(request.headers)
        user_agent = headers.get("user-agent", "")
        body = ""  # 不读取 body，避免消耗请求体影响下游；path/query/headers 已覆盖大部分攻击

        hits = scan_request(method, path, query, body, headers, user_agent)
        if not hits:
            return await call_next(request)

        attack_type = hits[0][0]
        signature_matched = hits[0][1]
        blocked = 0
        firewall_rule = ""

        try:
            ok, msg = block_ip_windows(client_ip)
            if ok:
                blocked = 1
                firewall_rule = msg
                logger.warning("IDS: 已封禁 %s 攻击来自 %s", attack_type, client_ip)
        except Exception as e:
            logger.warning("IDS: 防火墙封禁失败 %s", e)

        db = SessionLocal()
        try:
            evt = IDSEvent(
                client_ip=client_ip,
                attack_type=attack_type,
                signature_matched=signature_matched[:128],
                method=method,
                path=path[:512],
                query_snippet=query[:500],
                body_snippet=body[:500] if body else "",
                user_agent=user_agent[:512],
                headers_snippet=str(headers)[:1000],
                blocked=blocked,
                firewall_rule=firewall_rule[:256],
            )
            db.add(evt)
            db.commit()
        except Exception as e:
            logger.warning("IDS: 留痕写入失败 %s", e)
            db.rollback()
        finally:
            db.close()

        return JSONResponse(
            status_code=403,
            content={
                "detail": "请求已被安全策略拦截",
                "code": "IDS_BLOCKED",
                "attack_type": attack_type,
            },
        )
