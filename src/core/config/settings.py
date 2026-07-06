from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    jwt_secret_key: str  # load from .env — NEVER hardcode, NEVER commit
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.

    lru_cache ensures Settings() is constructed once per process,
    not re-parsed from the environment on every call. This matters
    because Settings will be injected as a FastAPI dependency into
    many endpoints — we don't want to re-read and re-validate env
    vars on every single request.
    """
    return Settings()