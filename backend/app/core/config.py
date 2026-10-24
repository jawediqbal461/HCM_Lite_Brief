from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Resolved from the backend directory, not the process cwd, so `uvicorn app.main:app`
    # picks up the same .env whether it is run from backend/ or the repo root.
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hcm_user:hcm_pass@localhost:5432/hcm_lite"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    admin_email: str | None = None
    admin_password: str | None = None

    ai_provider: str = "anthropic"
    ai_api_key: str | None = None
    ai_model: str = "claude-sonnet-4-5"

    # Comma-separated so a deployment can allow its hosted frontend alongside local dev.
    frontend_origin: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
