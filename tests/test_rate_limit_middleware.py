"""RateLimitMiddleware testlari (Redis token-bucket flood-control).

Tekshiriladi: limit ichida o'tadi, token tugagach to'siladi va xabar
yuboriladi, admin butunlay istisno, va Redis ishlamasa FAIL-OPEN (hech
kimni to'smaydi — bot butunlay ishlamay qolmasin).

Haqiqiy Lua Redis'da bajariladi — testda uni Python'da sodiq simulyatsiya
qiluvchi fake ishlatiladi (token bucket semantikasi bir xil).
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.middlewares.rate_limit import RateLimitMiddleware
from tests.helpers import make_bot, make_message


class _FakeTokenBucketRedis:
    """redis.eval(TOKEN_BUCKET_LUA, ...) ni Python'da simulyatsiya qiladi."""

    def __init__(self) -> None:
        self.buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, ts_ms)

    async def eval(self, _script: str, _numkeys: int, key: str, capacity: str, refill: str) -> int:
        cap = float(capacity)
        refill_per_sec = float(refill)
        now_ms = time.time() * 1000

        tokens, ts = self.buckets.get(key, (cap, now_ms))
        elapsed_sec = max(0.0, now_ms - ts) / 1000
        tokens = min(cap, tokens + elapsed_sec * refill_per_sec)

        allowed = 0
        if tokens >= 1:
            tokens -= 1
            allowed = 1

        self.buckets[key] = (tokens, now_ms)
        return allowed


class _BrokenRedis:
    """Redis ulanish xatosini simulyatsiya qiladi."""

    async def eval(self, *_args) -> int:  # noqa: ANN002
        raise ConnectionError("redis ishlamayapti")


def _data(message) -> dict:  # noqa: ANN001
    return {"event_from_user": message.from_user, "lang": "uz"}


@pytest.mark.asyncio
async def test_under_limit_calls_handler() -> None:
    middleware = RateLimitMiddleware(_FakeTokenBucketRedis())
    bot = make_bot()
    message = make_message(bot, 555_555)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, _data(message))

    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_over_limit_blocks_and_notifies() -> None:
    redis = _FakeTokenBucketRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    user_id = 555_555
    handler = AsyncMock(return_value="ok")

    # Sig'im (burst) tugaguncha — hammasi o'tadi.
    for _ in range(settings.rate_limit_per_minute):
        message = make_message(bot, user_id)
        result = await middleware(handler, message, _data(message))
        assert result == "ok"

    # Tokenlar tugadi — keyingi urinish to'siladi.
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
    redis = _FakeTokenBucketRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    handler = AsyncMock(return_value="ok")

    for _ in range(settings.rate_limit_per_minute):
        message = make_message(bot, 111_111)
        await middleware(handler, message, _data(message))

    other = make_message(bot, 222_222)
    result = await middleware(handler, other, _data(other))
    assert result == "ok"


@pytest.mark.asyncio
async def test_admin_bypasses_rate_limit_entirely() -> None:
    redis = _FakeTokenBucketRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    handler = AsyncMock(return_value="ok")

    for _ in range(settings.rate_limit_per_minute + 5):
        message = make_message(bot, admin_id)
        result = await middleware(handler, message, _data(message))
        assert result == "ok"

    assert redis.buckets == {}  # admin uchun bucket umuman ishlatilmagan


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
    redis = _FakeTokenBucketRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    message = make_message(bot, 555_555)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {"lang": "uz"})

    assert result == "ok"
    handler.assert_awaited_once()
    assert redis.buckets == {}


@pytest.mark.asyncio
async def test_tokens_refill_over_time() -> None:
    """Vaqt o'tishi bilan tokenlar tiklanadi (sliding xususiyat)."""
    redis = _FakeTokenBucketRedis()
    middleware = RateLimitMiddleware(redis)
    bot = make_bot()
    user_id = 999_999
    handler = AsyncMock(return_value="ok")

    for _ in range(settings.rate_limit_per_minute):
        message = make_message(bot, user_id)
        await middleware(handler, message, _data(message))

    # Bucket bo'shadi — qo'lda 10 soniya "orqaga" suramiz (refill simulyatsiyasi)
    tokens, ts = redis.buckets[f"rl:{user_id}"]
    redis.buckets[f"rl:{user_id}"] = (tokens, ts - 10_000)

    handler.reset_mock()
    message = make_message(bot, user_id)
    result = await middleware(handler, message, _data(message))

    # 10s * (limit/60) token tiklangan bo'lishi kerak (limit>=6 da >=1 token)
    assert result == "ok"
    handler.assert_awaited_once()
