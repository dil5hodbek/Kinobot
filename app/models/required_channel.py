"""Majburiy obuna kanali modeli (dinamik boshqarish uchun)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RequiredChannel(Base):
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
