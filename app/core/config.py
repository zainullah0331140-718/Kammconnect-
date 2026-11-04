from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "KaamConnect"
    app_env: str = "development"
    app_debug: bool = False
    secret_key: str = Field(..., min_length=32)
    database_url: str = Field(...)
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    frontend_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    upload_directory: str = "uploads"
    max_upload_mb: int = 2
    cookie_secure: bool = False
    reviews_require_approval: bool = False
    reviews_require_verified_provider: bool = True
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    password_reset_expire_minutes: int = 30
    password_reset_max_attempts: int = 5
    password_reset_window_seconds: int = 900
    password_reset_base_url: str | None = None
    password_reset_expose_token: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@kaamconnect.local"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    default_page_size: int = 12
    max_page_size: int = 100

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        weak_values = {
            "change-me",
            "changeme",
            "secret",
            "your-secret-key",
            "replace-with-a-long-random-secret",
            "change_me_generate_with_python_secrets",
            "replace-with-a-long-random-secret-at-least-32-chars",
        }
        if value.strip().lower() in weak_values:
            raise ValueError("SECRET_KEY must be a strong, unique value")
        return value

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_directory)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    @property
    def ads_upload_path(self) -> Path:
        return self.upload_path / "ads"

    @property
    def profiles_upload_path(self) -> Path:
        return self.upload_path / "profiles"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def access_cookie_name(self) -> str:
        return "kc_access"

    @property
    def refresh_cookie_name(self) -> str:
        return "kc_refresh"

    @property
    def csrf_cookie_name(self) -> str:
        return "kc_csrf"

    @property
    def password_reset_origin(self) -> str:
        if self.password_reset_base_url:
            return self.password_reset_base_url.rstrip("/")
        origins = self.frontend_origin_list
        return origins[0].rstrip("/") if origins else "http://localhost:8000"

    @property
    def expose_password_reset_link(self) -> bool:
        if self.password_reset_expose_token:
            return True
        return not self.is_production and not self.smtp_host


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
