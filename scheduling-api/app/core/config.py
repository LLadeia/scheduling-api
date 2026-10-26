from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: SecretStr
    jwt_issuer: str = "scheduling-api"
    jwt_audience: str = "scheduling-clients"
    access_token_minutes: int = Field(default=15, ge=1, le=1440)
    login_limit: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=60, ge=1)
    availability_max_days: int = Field(default=31, ge=1, le=366)

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("Use PostgreSQL com driver asyncpg")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def strong_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET deve ter pelo menos 32 caracteres aleatórios")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
