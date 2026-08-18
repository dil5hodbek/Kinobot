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

    # === DATABASE (pool) ===
    # Standart SQLAlchemy qiymatlari (pool_size=5, max_overflow=10) kam
    # auditoriyali botga yetadi, lekin ko'p bir vaqtdagi foydalanuvchida
    # navbat hosil qiladi. Aniq sozlab, .env orqali kerak bo'lsa oshirish
    # mumkin qilamiz.
    db_pool_size: int = Field(20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, alias="DB_MAX_OVERFLOW")
    # Uzoq turgan ulanishni davriy yangilaydi (masalan Postgres/tarmoq
    # oraliqda qayta ishga tushsa, "eskirgan" ulanishda osilib qolmaslik).
    db_pool_recycle_sec: int = Field(1800, alias="DB_POOL_RECYCLE_SEC")

    # === REDIS ===
    redis_host: str = Field("redis", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")
    # Bitta jarayonda Redis'ga bir vaqtda ochiq ulanishlar chegarasi.
    redis_max_connections: int = Field(50, alias="REDIS_MAX_CONNECTIONS")

    # === APP ===
    default_language: str = Field("uz", alias="DEFAULT_LANGUAGE")
    trend_limit: int = Field(10, alias="TREND_LIMIT")
    search_similarity_threshold: float = Field(0.2, alias="SEARCH_SIMILARITY_THRESHOLD")
    rate_limit_per_minute: int = Field(20, alias="RATE_LIMIT_PER_MINUTE")
    protect_content: bool = Field(True, alias="PROTECT_CONTENT")

    # === REKLAMA (har bir kino yuborilganda tugma sifatida qo'shiladi) ===
    promo_bot_username: str = Field("SpoylerBot", alias="PROMO_BOT_USERNAME")
    promo_channel_username: str = Field("spoylerkino", alias="PROMO_CHANNEL_USERNAME")

    # === ISHGA TUSHIRISH REJIMI ===
    # "production"da Redis MAJBURIY (MemoryStorage fallback taqiqlanadi —
    # restart FSM holatini yo'qotadi, bir nechta instans esa umuman buziladi).
    bot_env: str = Field("production", alias="BOT_ENV")
    # "polling" (standart) yoki "webhook". Webhook uchun WEBHOOK_URL shart.
    bot_mode: str = Field("polling", alias="BOT_MODE")
    webhook_url: str = Field("", alias="WEBHOOK_URL")
    webhook_secret: str = Field("", alias="WEBHOOK_SECRET")
    # Health/metrics/webhook HTTP serveri porti (konteyner ichida).
    http_port: int = Field(8080, alias="HTTP_PORT")

    # === POOL (qo'shimcha) ===
    # Pool band bo'lsa connection kutish chegarasi — cheksiz osilib qolmaslik.
    db_pool_timeout_sec: int = Field(10, alias="DB_POOL_TIMEOUT_SEC")

    # === MONITORING ===
    sentry_dsn: str = Field("", alias="SENTRY_DSN")

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
