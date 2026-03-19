"""IDS 引擎：特征匹配、攻击识别、Windows 防火墙封禁"""
import re
import subprocess
import platform
from urllib.parse import unquote

# 攻击特征库（正则）
SIGNATURES = [
    # SQL 注入
    (r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|exec\s*\(|0x[0-9a-f]+|'?\s*or\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|benchmark\s*\()", "sql_injection"),
    (r"(?i)(;?\s*--\s*$|/\*.*\*/|@@version|concat\s*\()", "sql_injection"),
    # XSS
    (r"(?i)(<script|javascript:|onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=|eval\s*\(|document\.cookie|alert\s*\()", "xss"),
    (r"(?i)(<iframe|<img\s+[^>]*onerror|vbscript:|expression\s*\()", "xss"),
    # 路径遍历
    (r"\.\.(/|\\|%2f|%5c)", "path_traversal"),
    (r"(?i)(/etc/passwd|/etc/shadow|c:\\windows\\system32)", "path_traversal"),
    # 命令注入
    (r"[;&|]\s*(ls|cat|id|whoami|pwd|dir|cmd|powershell|wget|curl)\s*", "cmd_injection"),
    (r"(?i)(\$\s*\(|`[^`]+`|system\s*\(|exec\s*\(|passthru\s*\(|shell_exec\s*\()", "cmd_injection"),
    # 常见扫描器/漏洞探测
    (r"(?i)(nikto|sqlmap|nmap|acunetix|nessus|burp|w3af)", "scanner"),
    (r"(?i)(\.git/|\.env|phpinfo|wp-admin|admin\.php|config\.php)", "scanner"),
    (r"(?i)(/etc/passwd|boot\.ini|web\.config|\.htaccess)", "scanner"),
    # 异常请求
    (r"(?i)(\x00|\x0d\x0a|\r\n\r\n\r\n)", "malformed"),
]

# 白名单路径（不检测）
WHITELIST_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/purchase/my",  # 教师「我的申请」接口，避免误拦
    "/",
    "/favicon.ico",
}


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


def scan_request(method: str, path: str, query: str, body: str | bytes | None, headers: dict, user_agent: str) -> list[tuple[str, str]]:
    """特征匹配，返回 [(attack_type, signature_matched), ...]"""
    path_decoded = unquote(path or "")
    query_decoded = unquote(query or "")
    body_str = _extract_text(body)
    ua = _extract_text(user_agent, 512)
    headers_str = " ".join(f"{k}:{v}" for k, v in (headers or {}).items())[:1024]

    combined = f"{method} {path_decoded} {query_decoded} {body_str} {ua} {headers_str}".lower()
    combined_raw = f"{path_decoded} {query_decoded} {body_str}"

    hits = []
    for pattern, atype in SIGNATURES:
        try:
            if re.search(pattern, combined, re.IGNORECASE | re.DOTALL) or re.search(pattern, combined_raw, re.IGNORECASE | re.DOTALL):
                hits.append((atype, pattern[:64]))
        except re.error:
            pass
    return hits


def block_ip_windows(ip: str) -> tuple[bool, str]:
    """调用 Windows 防火墙封禁 IP，返回 (成功, 消息)"""
    if platform.system() != "Windows":
        return False, "非 Windows 系统，跳过防火墙封禁"
    ip = ip.strip()
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return False, "不封禁本地地址"
    rule_name = f"IDS-Block-{ip.replace('.', '-').replace(':', '-')}"[:64]
    try:
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
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
        return False, "netsh 执行超时"
    except Exception as e:
        return False, str(e)


def is_whitelisted(path: str) -> bool:
    if not path:
        return False
    p = path.split("?")[0].rstrip("/") or "/"
    return p in WHITELIST_PATHS or any(p.startswith(w.replace("*", "")) for w in WHITELIST_PATHS if "*" in w)
