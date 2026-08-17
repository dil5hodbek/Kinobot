"""chat_cleanup_service testlari: xabar kuzatuvi (ZSET) va o'chirish."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import DeleteMessage

from app.services.chat_cleanup_service import (
    WINDOW_SECONDS,
    delete_messages,
    log_message,
    pop_recent_message_ids,
)
from tests.helpers import BrokenRedis, FakeZSetRedis, make_bot


@pytest.mark.asyncio
async def test_log_message_then_pop_returns_it() -> None:
    redis = FakeZSetRedis()
    await log_message(redis, chat_id=555, message_id=101)
    await log_message(redis, chat_id=555, message_id=102)

    ids = await pop_recent_message_ids(redis, chat_id=555)

    assert sorted(ids) == [101, 102]


@pytest.mark.asyncio
async def test_pop_clears_the_list() -> None:
    redis = FakeZSetRedis()
    await log_message(redis, chat_id=555, message_id=101)

    first = await pop_recent_message_ids(redis, chat_id=555)
    second = await pop_recent_message_ids(redis, chat_id=555)

    assert first == [101]
    assert second == []


@pytest.mark.asyncio
async def test_old_entries_outside_window_are_excluded() -> None:
    import time

    redis = FakeZSetRedis()
    now = time.time()
    # 48 soatdan ancha oldingi xabar — qo'lda eski score bilan qo'shamiz.
    await redis.zadd("chatlog:555", {"999": now - WINDOW_SECONDS - 3600})
    await redis.zadd("chatlog:555", {"1000": now})

    ids = await pop_recent_message_ids(redis, 555)

    assert 999 not in ids
    assert 1000 in ids


@pytest.mark.asyncio
async def test_different_chats_are_isolated() -> None:
    redis = FakeZSetRedis()
    await log_message(redis, chat_id=1, message_id=11)
    await log_message(redis, chat_id=2, message_id=22)

    ids_chat1 = await pop_recent_message_ids(redis, chat_id=1)
    ids_chat2 = await pop_recent_message_ids(redis, chat_id=2)

    assert ids_chat1 == [11]
    assert ids_chat2 == [22]


@pytest.mark.asyncio
async def test_log_message_fails_open_on_redis_error() -> None:
    # Xato ko'tarilmasligi kerak — kuzatuv ishlamasa ham bot davom etadi.
    await log_message(BrokenRedis(), chat_id=1, message_id=1)


@pytest.mark.asyncio
async def test_pop_fails_open_and_returns_empty_list() -> None:
    result = await pop_recent_message_ids(BrokenRedis(), chat_id=1)
    assert result == []


@pytest.mark.asyncio
async def test_delete_messages_counts_successes() -> None:
    bot = make_bot()
    bot.session.return_value = None

    deleted = await delete_messages(bot, chat_id=1, message_ids=[10, 20, 30])

    assert deleted == 3
    assert bot.session.await_count == 3


@pytest.mark.asyncio
async def test_delete_messages_skips_already_gone_messages() -> None:
    bot = make_bot()

    async def _side_effect(_bot, method, **_kwargs):  # noqa: ANN001
        if isinstance(method, DeleteMessage) and method.message_id == 20:
            raise TelegramBadRequest(method=method, message="message to delete not found")
        return True

    bot.session.side_effect = _side_effect

    deleted = await delete_messages(bot, chat_id=1, message_ids=[10, 20, 30])

    assert deleted == 2


@pytest.mark.asyncio
async def test_delete_messages_retries_after_flood_wait() -> None:
    bot = make_bot()
    calls = {"n": 0}

    async def _side_effect(_bot, method, **_kwargs):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise TelegramRetryAfter(method=method, message="flood", retry_after=0)
        return True

    bot.session.side_effect = _side_effect

    deleted = await delete_messages(bot, chat_id=1, message_ids=[10])

    assert deleted == 1
    assert calls["n"] == 2
