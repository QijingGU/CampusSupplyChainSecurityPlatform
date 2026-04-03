"""IDS detection engine for in-process request matching and firewall actions."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from urllib.parse import unquote

from .ids_rulepacks import get_runtime_active_signatures

# Business paths that should not be blocked by the inline matcher.
WHITELIST_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/purchase/my",
    "/api/upload",
    "/",
    "/favicon.ico",
}

# Read-only/query endpoints where SQL-like terms are common in legitimate requests.
WHITELIST_PATH_PREFIXES = (
    "/api/stock/",
    "/api/goods",
    "/api/trace/",
)


def _extract_text(s: str | bytes | None, max_len: int = 2000) -> str:
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8", errors="replace")
        except Exception:
            s = repr(s)[:max_len]
    s = str(s)[:max_len]
    return s.replace("\x00", "")


def scan_request_detailed(
    method: str,
    path: str,
    query: str,
    body: str | bytes | None,
    headers: dict,
    user_agent: str,
) -> dict:
    path_decoded = unquote(path or "")
    query_decoded = unquote(query or "")
    body_str = _extract_text(body)
    ua = _extract_text(user_agent, 512)
    headers_str = " ".join(f"{k}:{v}" for k, v in (headers or {}).items())[:1024]

    combined = f"{method} {path_decoded} {query_decoded} {body_str} {ua} {headers_str}".lower()
    combined_raw = f"{path_decoded} {query_decoded} {body_str}"

    signatures = get_runtime_active_signatures()
    hits: list[dict] = []
    score = 0
    type_weight: dict[str, int] = {}

    for pattern, attack_type, weight in signatures:
        try:
            matched = (
                re.search(pattern, combined, re.IGNORECASE | re.DOTALL)
                or re.search(pattern, combined_raw, re.IGNORECASE | re.DOTALL)
            )
            if not matched:
                continue
            hits.append({"attack_type": attack_type, "pattern": pattern[:96], "weight": weight})
            score += weight
            type_weight[attack_type] = type_weight.get(attack_type, 0) + weight
        except re.error:
            continue

    score = min(score, 100)
    if not hits:
        return {
            "matched": False,
            "attack_type": "",
            "signature_matched": "",
            "risk_score": 0,
            "confidence": 0,
            "hit_count": 0,
            "hits": [],
            "detect_detail": "[]",
        }

    primary_attack_type = max(type_weight.items(), key=lambda x: x[1])[0]
    primary_hit = next((h for h in hits if h["attack_type"] == primary_attack_type), hits[0])
    confidence = min(95, 40 + len(hits) * 12 + (20 if score >= 70 else 0))
    return {
        "matched": True,
        "attack_type": primary_attack_type,
        "signature_matched": str(primary_hit["pattern"])[:128],
        "risk_score": score,
        "confidence": confidence,
        "hit_count": len(hits),
        "hits": hits,
        "detect_detail": json.dumps(hits, ensure_ascii=False)[:8000],
    }


def scan_request(
    method: str,
    path: str,
    query: str,
    body: str | bytes | None,
    headers: dict,
    user_agent: str,
) -> list[tuple[str, str]]:
    detailed = scan_request_detailed(method, path, query, body, headers, user_agent)
    if not detailed.get("matched"):
        return []
    return [(detailed.get("attack_type", ""), detailed.get("signature_matched", ""))]


def block_ip_windows(ip: str) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "Non-Windows system; firewall block skipped."
    ip = ip.strip()
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return False, "Localhost addresses are not blocked."
    rule_name = f"IDS-Block-{ip.replace('.', '-').replace(':', '-')}"[:64]
    try:
        subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                f"name={rule_name}",
                "dir=in",
                "action=block",
                f"remoteip={ip}",
                "protocol=any",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True, rule_name
    except subprocess.TimeoutExpired:
        return False, "netsh execution timed out."
    except Exception as exc:
        return False, str(exc)


def unblock_ip_windows(ip: str) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "Non-Windows system; firewall unblock skipped."
    ip = ip.strip()
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return False, "Localhost addresses are not unblocked."
    rule_name = f"IDS-Block-{ip.replace('.', '-').replace(':', '-')}"[:64]
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True, rule_name
    except subprocess.TimeoutExpired:
        return False, "netsh execution timed out."
    except Exception as exc:
        return False, str(exc)


def is_whitelisted(path: str) -> bool:
    if not path:
        return False
    raw = path.split("?")[0]
    normalized = raw.rstrip("/") or "/"
    if normalized in WHITELIST_PATHS:
        return True
    if any(normalized.startswith(w.replace("*", "")) for w in WHITELIST_PATHS if "*" in w):
        return True
    for prefix in WHITELIST_PATH_PREFIXES:
        if raw == prefix.rstrip("/") or raw.startswith(prefix):
            return True
    return False
