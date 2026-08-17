"""RateLimitMiddleware testlari (Redis flood-control).

Tekshiriladi: limit ichida o'tadi, limitdan oshsa to'siladi va xabar
yuboriladi, admin butunlay istisno, va Redis ishlamasa FAIL-OPEN (hech
kimni to'smaydi — bot butunlay ishlamay qolmasin).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.middlewares.rate_limit import RateLimitMiddleware
from tests.helpers import make_bot, make_message


class _FakeRedis:
    """Redis o'rniga — xotiradagi hisoblagich (incr/expire)."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expired_keys: list[str] = []

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expired_keys.append(key)


class _BrokenRedis:
    """Redis ulanish xatosini simulyatsiya qiladi."""

    async def incr(self, key: str) -> int:  # noqa: ARG002
        raise ConnectionError("redis ishlamayapti")

    async def expire(self, key: str, seconds: int) -> None:  # noqa: ARG002
        raise ConnectionError("redis ishlamayapti")


def _data(message) -> dict:  # noqa: ANN001
    return {"event_from_user": message.from_user, "lang": "uz"}


@pytest.mark.asyncio
async def test_under_limit_calls_handler() -> None:
    middleware = RateLimitMiddleware(_FakeRedis())
    bot = make_bot()
    message = make_message(bot, 555_555)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, _data(message))

    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_over_limit_blocks_and_notifies() -> None:
    redis = _FakeRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    user_id = 555_555
    handler = AsyncMock(return_value="ok")

    # Limitgacha — hammasi o'tadi.
    for _ in range(settings.rate_limit_per_minute):
        message = make_message(bot, user_id)
        result = await middleware(handler, message, _data(message))
        assert result == "ok"

    # Limitdan keyingi (N+1) urinish — to'siladi.
    handler.reset_mock()
    bot.session.reset_mock()
    message = make_message(bot, user_id)
    result = await middleware(handler, message, _data(message))

    assert result is None
    handler.assert_not_awaited()
    bot.session.assert_awaited_once()  # "Sekinroq..." xabari yuborildi


@pytest.mark.asyncio
async def test_limit_is_per_user() -> None:
    """Bir foydalanuvchi to'silsa, boshqasi ta'sirlanmaydi."""
    redis = _FakeRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    handler = AsyncMock(return_value="ok")

    for _ in range(settings.rate_limit_per_minute):
        message = make_message(bot, 111_111)
        await middleware(handler, message, _data(message))

    # 111_111 endi to'silgan bo'lsa ham, boshqa user erkin.
    other = make_message(bot, 222_222)
    result = await middleware(handler, other, _data(other))
    assert result == "ok"


@pytest.mark.asyncio
async def test_admin_bypasses_rate_limit_entirely() -> None:
    redis = _FakeRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    handler = AsyncMock(return_value="ok")

    for _ in range(settings.rate_limit_per_minute + 5):
        message = make_message(bot, admin_id)
        result = await middleware(handler, message, _data(message))
        assert result == "ok"

    assert redis.counts == {}  # admin uchun hisoblagich umuman ishlatilmagan


@pytest.mark.asyncio
async def test_redis_failure_fails_open() -> None:
    """Redis ishdan chiqsa — hech kim to'silmasligi kerak (mavjudlik > qat'iylik)."""
    middleware = RateLimitMiddleware(_BrokenRedis())
    bot = make_bot()
    message = make_message(bot, 777_777)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, _data(message))

    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_from_user_calls_handler_without_limiting() -> None:
    """event_from_user yo'q (masalan kanal posti) — limitlanmaydi."""
    redis = _FakeRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    message = make_message(bot, 555_555)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {"lang": "uz"})  # event_from_user yo'q

    assert result == "ok"
    handler.assert_awaited_once()
    assert redis.counts == {}
