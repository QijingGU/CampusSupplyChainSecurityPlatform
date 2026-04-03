from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.ids_rulepack import IDSRulepackActivation, IDSRulepackRuntimeState

RULEPACK_RESULT_ACTIVATED = "activated"
RULEPACK_RESULT_REJECTED = "rejected"
RULEPACK_RESULT_FAILED = "failed"

TRUST_EXTERNAL_MATURE = "external_mature"
TRUST_TRANSITIONAL_LOCAL = "transitional_local"
TRUST_DEMO_TEST = "demo_test"

DEFAULT_RULEPACK_KEY = "legacy-inline"
RUNTIME_STATE_ROW_ID = 1


LEGACY_INLINE_SIGNATURES: list[tuple[str, str, int]] = [
    (
        r"(?i)(union\s+select|insert\s+into|drop\s+table|0x[0-9a-f]{4,}|'?\s*or\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|benchmark\s*\(|sleep\s*\(|waitfor\s+delay|pg_sleep\s*\()",
        "sql_injection",
        30,
    ),
    (r"(?i)(select\s+.{0,240}\s+from\s+|;?\s*--\s*$|/\*.{0,120}\*/|@@version|concat\s*\()", "sql_injection", 25),
    (r"(?i)(\bexec\s*\(|\bsp_executesql\b|\bxp_cmdshell\b)", "sql_injection", 30),
    (r"(?i)(<script[\s/>]|javascript:|onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=|eval\s*\(|document\.cookie|alert\s*\()", "xss", 24),
    (r"(?i)(<iframe|<img\s+[^>]*onerror|vbscript:|expression\s*\()", "xss", 22),
    (r"\.\.(/|\\|%2f|%2F|%5c|%5C)", "path_traversal", 26),
    (r"(?i)(/etc/passwd|/etc/shadow|boot\.ini|win\.ini|c:\\windows\\system32\\config)", "path_traversal", 30),
    (r"(?i)[;&|]\s*(ls|cat|id|whoami|pwd|dir|cmd\.exe|powershell|wget|curl|nc\s|netcat)\b", "cmd_injection", 28),
    (r"(?i)(\$\s*\(|`[^`\n]{1,200}`|\bsystem\s*\(|\bpassthru\s*\(|\bshell_exec\s*\(|\bpopen\s*\()", "cmd_injection", 28),
    (r"(?i)(\$\{jndi:|jndi:(ldap|dns|rmi)://|\$\{lower:|\$\{env:)", "jndi_injection", 35),
    (r"(?i)(__proto__|constructor\s*\.\s*prototype|\[\"__proto__\"\])", "prototype_pollution", 22),
    (r"(?i)(nikto|sqlmap|nmap|acunetix|nessus|\bburpsuite\b|w3af|masscan|zgrab)", "scanner", 16),
    (r"(?i)(/\.git/|/\.env\b|phpinfo\s*\(|wp-login\.php|wp-admin/setup|/administrator/|vendor/phpunit)", "scanner", 18),
    (r"(?i)(web\.config\b|\.htaccess\b|crossdomain\.xml|sftp-config\.json)", "scanner", 16),
    (r"(?i)(\x00|\r\n\r\n\r\n)", "malformed", 14),
]

MATURE_WEB_BALANCED_SIGNATURES: list[tuple[str, str, int]] = [
    (r"(?i)(union\s+all\s+select|union\s+select|information_schema|xp_cmdshell|load_file\s*\()", "sql_injection", 34),
    (r"(?i)(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|benchmark\s*\(|sleep\s*\(|pg_sleep\s*\()", "sql_injection", 30),
    (r"(?i)(<script[\s/>]|javascript:|onerror\s*=|onload\s*=|document\.cookie|fetch\s*\()", "xss", 26),
    (r"(?i)(<iframe|<svg[^>]*onload|<img\s+[^>]*onerror|vbscript:|data:text/html)", "xss", 24),
    (r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c|/etc/passwd|/etc/shadow)", "path_traversal", 30),
    (r"(?i)(cmd\.exe|powershell\s+-|bash\s+-c|/bin/sh|nc\s+-e|wget\s+http|curl\s+http)", "cmd_injection", 30),
    (r"(?i)(\$\{jndi:|jndi:(ldap|dns|rmi)://|log4j|marshalsec)", "jndi_injection", 36),
    (r"(?i)(__proto__|constructor\.prototype|prototype\[|prototype\.)", "prototype_pollution", 24),
    (r"(?i)(nikto|sqlmap|nmap|acunetix|nessus|w3af|masscan|zgrab|dirbuster)", "scanner", 18),
    (r"(?i)(/\.git/|/\.svn/|/\.env\b|wp-admin/setup|vendor/phpunit|composer\.json)", "scanner", 20),
    (r"(?i)(multipart/form-data.{0,80}(php|jsp|aspx|jspx)|webshell|cmd=)", "malware", 26),
    (r"(?i)(\x00|\r\n\r\n\r\n|content-length:\s*0\s*content-length:)", "malformed", 14),
]

DEMO_SEED_SIGNATURES: list[tuple[str, str, int]] = [
    (r"(?i)(demo-seed|training-payload|seed-only)", "scanner", 12),
]

RULEPACK_CATALOG: dict[str, dict] = {
    DEFAULT_RULEPACK_KEY: {
        "rulepack_key": DEFAULT_RULEPACK_KEY,
        "display_name": "Legacy Inline Pack",
        "pack_version": "2026.04",
        "trust_classification": TRUST_TRANSITIONAL_LOCAL,
        "detector_family": "web",
        "provenance_note": "Legacy local matcher signatures retained for compatibility fallback.",
        "signatures": LEGACY_INLINE_SIGNATURES,
    },
    "mature-web-balanced": {
        "rulepack_key": "mature-web-balanced",
        "display_name": "Mature Web Balanced Pack",
        "pack_version": "2026.04",
        "trust_classification": TRUST_EXTERNAL_MATURE,
        "detector_family": "web",
        "provenance_note": "Curated mature web signatures adapted from long-lived community pattern families.",
        "signatures": MATURE_WEB_BALANCED_SIGNATURES,
    },
    "demo-seed-pack": {
        "rulepack_key": "demo-seed-pack",
        "display_name": "Demo Seed Pack",
        "pack_version": "2026.04.demo",
        "trust_classification": TRUST_DEMO_TEST,
        "detector_family": "web",
        "provenance_note": "Demo-only signatures for training fixtures.",
        "signatures": DEMO_SEED_SIGNATURES,
    },
}

_runtime_active_rulepack_key = DEFAULT_RULEPACK_KEY


def list_rulepack_catalog() -> list[dict]:
    items: list[dict] = []
    for key in sorted(RULEPACK_CATALOG.keys()):
        entry = RULEPACK_CATALOG[key]
        items.append(
            {
                "rulepack_key": entry["rulepack_key"],
                "display_name": entry["display_name"],
                "pack_version": entry["pack_version"],
                "trust_classification": entry["trust_classification"],
                "detector_family": entry["detector_family"],
                "provenance_note": entry["provenance_note"],
                "rule_count": len(entry.get("signatures", [])),
            }
        )
    return items


def get_rulepack_definition(rulepack_key: str) -> dict | None:
    return RULEPACK_CATALOG.get((rulepack_key or "").strip())


def get_rulepack_signatures(rulepack_key: str) -> list[tuple[str, str, int]]:
    entry = get_rulepack_definition(rulepack_key)
    if not entry:
        entry = RULEPACK_CATALOG[DEFAULT_RULEPACK_KEY]
    signatures = entry.get("signatures", [])
    return list(signatures) if signatures else list(RULEPACK_CATALOG[DEFAULT_RULEPACK_KEY]["signatures"])


def get_runtime_active_rulepack_key() -> str:
    global _runtime_active_rulepack_key
    if _runtime_active_rulepack_key not in RULEPACK_CATALOG:
        _runtime_active_rulepack_key = DEFAULT_RULEPACK_KEY
    return _runtime_active_rulepack_key


def set_runtime_active_rulepack_key(rulepack_key: str) -> str:
    global _runtime_active_rulepack_key
    candidate = (rulepack_key or "").strip()
    if candidate not in RULEPACK_CATALOG:
        candidate = DEFAULT_RULEPACK_KEY
    _runtime_active_rulepack_key = candidate
    return _runtime_active_rulepack_key


def get_runtime_active_signatures() -> list[tuple[str, str, int]]:
    return get_rulepack_signatures(get_runtime_active_rulepack_key())


def ensure_runtime_state(db: Session) -> IDSRulepackRuntimeState:
    state = db.query(IDSRulepackRuntimeState).filter(IDSRulepackRuntimeState.id == RUNTIME_STATE_ROW_ID).first()
    if state:
        return state
    state = IDSRulepackRuntimeState(
        id=RUNTIME_STATE_ROW_ID,
        active_rulepack_key=DEFAULT_RULEPACK_KEY,
        updated_by="system_bootstrap",
        update_note="Initialized default runtime rulepack state.",
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def resolve_active_rulepack_key_from_db(db: Session) -> str:
    state = ensure_runtime_state(db)
    active_key = (state.active_rulepack_key or "").strip()
    if active_key not in RULEPACK_CATALOG:
        active_key = DEFAULT_RULEPACK_KEY
        state.active_rulepack_key = active_key
        state.update_note = "Invalid runtime state corrected to default rulepack."
        db.commit()
        db.refresh(state)
    set_runtime_active_rulepack_key(active_key)
    return active_key


def update_runtime_state(
    db: Session,
    *,
    active_rulepack_key: str,
    updated_by: str,
    update_note: str = "",
) -> IDSRulepackRuntimeState:
    state = ensure_runtime_state(db)
    state.active_rulepack_key = set_runtime_active_rulepack_key(active_rulepack_key)
    state.updated_by = (updated_by or "").strip()[:64]
    state.update_note = (update_note or "").strip()[:2000]
    db.commit()
    db.refresh(state)
    return state


def create_rulepack_activation_record(
    db: Session,
    *,
    rulepack_key: str,
    result_status: str,
    triggered_by: str,
    activation_detail: str,
) -> IDSRulepackActivation:
    entry = get_rulepack_definition(rulepack_key) or {}
    activation = IDSRulepackActivation(
        rulepack_key=(rulepack_key or "").strip()[:64],
        pack_version=(entry.get("pack_version") or "")[:64],
        trust_classification=(entry.get("trust_classification") or "")[:32],
        detector_family=(entry.get("detector_family") or "")[:32],
        result_status=(result_status or RULEPACK_RESULT_FAILED)[:32],
        activation_detail=(activation_detail or "")[:2000],
        triggered_by=(triggered_by or "").strip()[:64],
    )
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation
