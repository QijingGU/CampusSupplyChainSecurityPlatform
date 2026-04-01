"""IDS middleware for request inspection, event persistence, and blocking."""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings
from ..database import SessionLocal
from ..models.ids_event import IDSEvent
from ..services.ids_ai_analysis import schedule_ai_analysis
from ..services.ids_engine import _extract_text, block_ip_windows, is_whitelisted, scan_request_detailed
from ..services.ids_ingestion import (
    REAL_EVENT_ORIGIN,
    SOURCE_TRANSITIONAL_LOCAL,
    apply_source_metadata,
)

logger = logging.getLogger("ids")


def _get_client_ip(request: Request) -> str:
    for header in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
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
        body_str = ""
        body_bytes = b""

        if method in ("POST", "PUT", "PATCH", "DELETE") and settings.IDS_MAX_BODY_BYTES > 0:
            try:
                body_bytes = await request.body()
                cap = min(len(body_bytes), max(1, settings.IDS_MAX_BODY_BYTES))
                body_str = _extract_text(body_bytes[:cap], settings.IDS_MAX_BODY_BYTES)
            except Exception as exc:
                logger.debug("IDS body read skip: %s", exc)
                body_bytes = b""
                body_str = ""

            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = Request(request.scope, receive)

        detection = scan_request_detailed(method, path, query, body_str, headers, user_agent)
        if not detection.get("matched"):
            return await call_next(request)

        attack_type = str(detection.get("attack_type") or "")
        signature_matched = str(detection.get("signature_matched") or "")
        risk_score = int(detection.get("risk_score") or 0)
        confidence = int(detection.get("confidence") or 0)
        hit_count = int(detection.get("hit_count") or 0)
        detect_detail = str(detection.get("detect_detail") or "")
        blocked = 0
        firewall_rule = ""
        should_block = risk_score >= int(settings.IDS_BLOCK_THRESHOLD)
        status = "investigating"
        action_taken = "record_only"
        response_result = "record_only"
        response_detail = "recorded_without_block"

        if should_block and settings.IDS_FIREWALL_BLOCK:
            try:
                ok, msg = block_ip_windows(client_ip)
                if ok:
                    blocked = 1
                    firewall_rule = msg
                    logger.warning("IDS blocked %s from %s", attack_type, client_ip)
                    action_taken = "firewall_block"
                    response_result = "success"
                    response_detail = msg
                else:
                    action_taken = "block_failed_recorded"
                    response_result = "failed"
                    response_detail = msg
            except Exception as exc:
                logger.warning("IDS firewall block failed: %s", exc)
                action_taken = "block_failed_recorded"
                response_result = "failed"
                response_detail = str(exc)
        elif should_block:
            action_taken = "logical_block_only"
            response_detail = "threshold_reached_without_firewall"

        db = SessionLocal()
        evt_id: int | None = None
        try:
            evt = IDSEvent(
                client_ip=client_ip,
                attack_type=attack_type,
                signature_matched=signature_matched[:128],
                method=method,
                path=path[:512],
                query_snippet=query[:500],
                body_snippet=(body_str or "")[:500],
                user_agent=user_agent[:512],
                headers_snippet=str(headers)[:1000],
                blocked=blocked,
                firewall_rule=firewall_rule[:256],
                status=status,
                action_taken=action_taken,
                response_result=response_result,
                response_detail=response_detail[:1000],
                risk_score=risk_score,
                confidence=confidence,
                hit_count=hit_count,
                detect_detail=detect_detail,
            )
            apply_source_metadata(
                evt,
                event_origin=REAL_EVENT_ORIGIN,
                source_classification=SOURCE_TRANSITIONAL_LOCAL,
                detector_family="web",
                detector_name="inline_request_matcher",
                source_rule_id=signature_matched[:128],
                source_rule_name=attack_type,
                source_version="legacy-inline",
                source_freshness="current",
            )
            db.add(evt)
            db.commit()
            db.refresh(evt)
            evt_id = evt.id
        except Exception as exc:
            logger.warning("IDS event persistence failed: %s", exc)
            db.rollback()
        finally:
            db.close()

        if evt_id is not None:
            schedule_ai_analysis(evt_id)

        if should_block:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Request blocked by IDS security policy",
                    "code": "IDS_BLOCKED",
                    "attack_type": attack_type,
                    "risk_score": risk_score,
                    "confidence": confidence,
                },
            )
        return await call_next(request)
