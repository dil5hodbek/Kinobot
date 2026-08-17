"""Ilova konfiguratsiyasi (pydantic-settings orqali .env dan o'qiladi)."""
from __future__ import annotations

from functools import cached_property, lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha konfiguratsiya qiymatlari .env fayldan olinadi.

    ADMIN_IDS va REQUIRED_CHANNELS xom (str) sifatida o'qilib, keyin
    property orqali ro'yxatga aylantiriladi (pydantic-settings ning JSON
    parsingiga tushib qolmaslik uchun).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # === BOT ===
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # === ADMIN ===
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")
    admin_phone: str = Field("", alias="ADMIN_PHONE")

    # === STORAGE ===
    storage_channel_id: int = Field(..., alias="STORAGE_CHANNEL_ID")

    # === REQUIRED CHANNELS (.env) ===
    required_channels_raw: str = Field("", alias="REQUIRED_CHANNELS")

    # === DATABASE ===
    postgres_host: str = Field("postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_db: str = Field("kinobot", alias="POSTGRES_DB")
    postgres_user: str = Field("kinobot", alias="POSTGRES_USER")
    postgres_password: str = Field(..., alias="POSTGRES_PASSWORD")

    # === REDIS ===
    redis_host: str = Field("redis", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")

    # === APP ===
    default_language: str = Field("uz", alias="DEFAULT_LANGUAGE")
    trend_limit: int = Field(10, alias="TREND_LIMIT")
    search_similarity_threshold: float = Field(0.2, alias="SEARCH_SIMILARITY_THRESHOLD")
    rate_limit_per_minute: int = Field(20, alias="RATE_LIMIT_PER_MINUTE")
    protect_content: bool = Field(True, alias="PROTECT_CONTENT")

    @cached_property
    def admin_ids(self) -> list[int]:
        return [
            int(x.strip())
            for x in self.admin_ids_raw.split(",")
            if x.strip().lstrip("-").isdigit()
        ]

    @cached_property
    def required_channels(self) -> list[str]:
        return [
            x.strip().lstrip("@")
            for x in self.required_channels_raw.split(",")
            if x.strip()
        ]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Konfiguratsiyani bir marta o'qib, keshlab qaytaradi."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
