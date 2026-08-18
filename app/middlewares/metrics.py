"""Har bir update uchun Prometheus metrikalar (son, davomiylik, xato).

dp.update.outer_middleware sifatida ENG BIRINCHI ro'yxatga olinadi —
butun pipeline (DB sessiya, handlerlar) o'lchovga kiradi.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.observability.metrics import (
    update_duration_seconds,
    update_errors_total,
    updates_total,
)


class MetricsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        updates_total.inc()
        try:
            return await handler(event, data)
        except Exception:
            update_errors_total.inc()
            raise
        finally:
            update_duration_seconds.observe(time.monotonic() - start)
