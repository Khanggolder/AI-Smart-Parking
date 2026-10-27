"""Configuration read from repository-root .env or process environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = "postgresql://parking_user:change_me@localhost:5432/parking"
    app_env: str = "development"
    # Deliberately no default signing key; set JWT_SECRET_KEY in the local .env.
    jwt_secret_key: str | None = None
    jwt_expire_minutes: int = 60
    upload_max_mb: int = 10
    reference_image_dir: str = "backend/storage/reference-images"
    # Comma-separated trusted local React origins; no wildcard in dev.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def reference_image_root(self) -> Path:
        path = Path(self.reference_image_dir)
        return (path if path.is_absolute() else REPOSITORY_ROOT / path).resolve()

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
