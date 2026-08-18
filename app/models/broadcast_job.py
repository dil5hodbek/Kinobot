"""Durable broadcast job modeli.

Broadcast endi jarayon xotirasidagi asyncio.Task emas — DB'dagi yozuv.
Bot restart bo'lsa `last_processed_user_id` kursoridan davom etadi
(at-least-once semantika: eng yomon holatda oxirgi to'liq saqlanmagan
batch qayta yuborilishi mumkin — bu hujjatlashtirilgan, exactly-once
Telegram API bilan umuman mumkin emas).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # pending | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending", server_default="pending"
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lang: Mapped[str] = mapped_column(
        String(5), nullable=False, default="uz", server_default="uz"
    )
    total_recipients: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    sent_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    blocked_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    failed_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    # users.id bo'yicha keyset kursor (telegram_id emas — barqaror tartib uchun)
    last_processed_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
