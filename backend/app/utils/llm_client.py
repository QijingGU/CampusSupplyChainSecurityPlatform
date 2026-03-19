"""LLM 调用封装：支持 Ollama / OpenAI 兼容 API / Function Calling"""
import json
import logging
from ..config import settings
import httpx

logger = logging.getLogger(__name__)


def _ollama_chat(messages: list[dict], model: str) -> str:
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/api/chat"
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, json={"model": model, "messages": messages, "stream": False})
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")


def _openai_chat(messages: list[dict], model: str) -> str:
    base = (settings.LLM_BASE_URL or "https://api.openai.com").rstrip("/")
    path = "/chat/completions" if settings.LLM_PROVIDER == "deepseek" else "/v1/chat/completions"
    url = base + path
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY or ''}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers, json={"model": model, "messages": messages})
        r.raise_for_status()
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def chat(messages: list[dict], model: str | None = None) -> str | None:
    """调用 LLM，失败返回 None"""
    if not settings.LLM_BASE_URL and settings.LLM_PROVIDER != "openai":
        return None
    model = model or settings.LLM_MODEL
    try:
        if settings.LLM_PROVIDER == "ollama":
            return _ollama_chat(messages, model)
        if settings.LLM_PROVIDER in ("openai", "deepseek"):
            return _openai_chat(messages, model)
    except Exception as e:
        import traceback
        logger.warning("LLM 调用失败: %s\n%s", str(e), traceback.format_exc())
        print(f"[LLM] 调用失败: {e}")
    return None


def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str | None = None,
) -> tuple[str | None, list[dict]]:
    """
    调用 LLM（支持 Function Calling），返回 (content, tool_calls)。
    tool_calls 格式: [{"id": "...", "name": "fn", "arguments": {...}}, ...]
    仅 DeepSeek/OpenAI 支持，Ollama 降级为普通 chat。
    """
    model = model or settings.LLM_MODEL
    if settings.LLM_PROVIDER == "ollama":
        # Ollama 大多数模型不支持 tools，降级为普通对话
        content = _ollama_chat(messages, model)
        return (content, []) if content else (None, [])

    base = (settings.LLM_BASE_URL or "https://api.openai.com").rstrip("/")
    path = "/chat/completions" if settings.LLM_PROVIDER == "deepseek" else "/v1/chat/completions"
    url = base + path
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY or ''}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "tools": tools}

    try:
        with httpx.Client(timeout=90.0) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content") or ""
        raw_tool_calls = msg.get("tool_calls") or []
        tool_calls = []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            args_str = fn.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": args,
            })
        return (content.strip() if content else None, tool_calls)
    except Exception as e:
        import traceback
        logger.warning("LLM tools 调用失败: %s\n%s", str(e), traceback.format_exc())
        print(f"[LLM] tools 调用失败: {e}")
        return (None, [])
