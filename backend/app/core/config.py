from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
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

    database_url: str = "postgresql+psycopg://vocab:vocab@localhost:5432/vocab"
    database_echo: bool = False

    upload_dir: Path = Field(default=Path("uploads"))
    max_upload_size_mb: int = Field(default=20, gt=0)

    @field_validator("upload_dir")
    @classmethod
    def resolve_upload_dir(cls, value: Path) -> Path:
        return value if value.is_absolute() else (BASE_DIR / value).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
