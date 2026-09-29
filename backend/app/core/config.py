from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory — makes .env and upload paths independent of the current working directory.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "German Vocabulary Trainer API"
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = False
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://vocab:vocab@127.0.0.1:5432/vocab"
    database_echo: bool = False

    upload_dir: Path = Field(default=Path("uploads"))
    # Built frontend (``npm run build`` → frontend/dist) served next to the API. None = API only
    # (development uses the Vite dev server instead).
    frontend_dist_dir: Path | None = None
    max_upload_size_mb: int = Field(default=20, gt=0)

    # Login sessions (cookie). Secure cookies need HTTPS; enable them in production.
    session_cookie_name: str = "spektrum_session"
    session_cookie_secure: bool = False
    session_days: int = Field(default=30, gt=0)

    ai_provider: Literal["gemini"] = "gemini"
    # Pages sent to the AI in one vocabulary-extraction request; long chapters are split.
    ai_max_pages_per_request: int = Field(default=5, gt=0)
    # Parallel vocabulary-extraction requests during one analysis.
    ai_max_concurrency: int = Field(default=4, gt=0)
    # Client-side request budget per model (Gemini free tier: 5). None = no limit.
    ai_requests_per_minute: int | None = Field(default=None, gt=0)
    ai_request_timeout_seconds: int = Field(default=180, gt=0)
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Hosted providers (Neon, Fly) hand out postgres:// URLs; SQLAlchemy needs the driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @field_validator("upload_dir", "frontend_dist_dir")
    @classmethod
    def resolve_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return value if value.is_absolute() else (BASE_DIR / value).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
