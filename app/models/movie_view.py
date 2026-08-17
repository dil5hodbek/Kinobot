"""Ko'rishlar tarixi modeli (statistika uchun)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MovieView(Base):
    __tablename__ = "movie_views"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movies.id"), nullable=False
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
