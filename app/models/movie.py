"""Kino modeli."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    # "channel" — yopiq kanaldan copy_message bilan yuboriladi (channel_id/
    # message_id majburiy). "link" — tashqi havola tugma bilan yuboriladi
    # (external_url majburiy). Qaysi kombinatsiya to'g'ri ekanini baza
    # darajasida CHECK constraint (ck_movies_source_fields) kafolatlaydi.
    source_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="channel", server_default="channel"
    )
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Janr bo'yicha guruhlash (bot "romance" kabi so'rovlarni shu bo'yicha
    # filtrlaydi) — index=True ko'p auditoriyada sekinlashmasin.
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    views_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
