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
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    views_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
