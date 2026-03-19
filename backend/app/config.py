from pathlib import Path
import os
from pydantic_settings import BaseSettings
from pydantic import field_validator

# 确保从 backend 目录加载 .env（无论启动路径）
_env_file = Path(__file__).resolve().parent.parent / ".env"

# 强制预先加载 .env（覆盖可能存在的空值，解决 uvicorn 子进程环境不同步）
if _env_file.exists():
    with open(_env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v  # 直接覆盖，确保 .env 生效


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./supply_chain.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # CORS（开发/演示放宽，生产请收紧）
    # 通过 Nginx 同源部署时无需修改；同一局域网可加 http://本机IP:80 或 :5173
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",  # vite preview
        "http://localhost:8166", "http://127.0.0.1:8166",  # 同源直连
        "http://localhost", "http://127.0.0.1",  # 小皮 80 端口
    ]

    # LLM 智能体（可选，不配置则用规则引擎）
    LLM_PROVIDER: str = "ollama"  # ollama | openai | deepseek
    LLM_BASE_URL: str | None = None  # 如 http://127.0.0.1:11434 则启用 Ollama
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "qwen2:7b"  # Ollama 模型名，或 openai 的 model

    @field_validator("LLM_BASE_URL", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    class Config:
        env_file = str(_env_file) if _env_file.exists() else None
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
