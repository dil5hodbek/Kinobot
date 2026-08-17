"""chat_cleanup_service testlari: xabar kuzatuvi (ZSET) va o'chirish."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import DeleteMessages

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
    """1-100 ta id bitta `deleteMessages` chaqiruviga sig'adi — bitta so'rov."""
    bot = make_bot()
    bot.session.return_value = True

    deleted = await delete_messages(bot, chat_id=1, message_ids=[10, 20, 30])

    assert deleted == 3
    assert bot.session.await_count == 1
    method = bot.session.call_args.args[1]
    assert isinstance(method, DeleteMessages)
    assert method.message_ids == [10, 20, 30]


@pytest.mark.asyncio
async def test_delete_messages_chunks_by_100() -> None:
    """150 ta id -> 2 ta chunk (100 + 50), 2 ta alohida `deleteMessages` chaqiruvi."""
    bot = make_bot()
    bot.session.return_value = True
    ids = list(range(1, 151))

    deleted = await delete_messages(bot, chat_id=1, message_ids=ids)

    assert deleted == 150
    assert bot.session.await_count == 2
    first_chunk = bot.session.call_args_list[0].args[1].message_ids
    second_chunk = bot.session.call_args_list[1].args[1].message_ids
    assert len(first_chunk) == 100
    assert len(second_chunk) == 50


@pytest.mark.asyncio
async def test_delete_messages_chunk_level_failure_excludes_that_chunk() -> None:
    """Butun chunk chaqiruvi xato bersa (masalan tarmoq xatosi) — faqat o'sha
    chunk hisoblanmaydi, boshqa chunklar davom etadi."""
    bot = make_bot()
    calls = {"n": 0}

    async def _side_effect(_bot, method, **_kwargs):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise TelegramBadRequest(method=method, message="bad request")
        return True

    bot.session.side_effect = _side_effect
    ids = list(range(1, 151))

    deleted = await delete_messages(bot, chat_id=1, message_ids=ids)

    assert deleted == 50  # faqat 2-chunk (50 ta) muvaffaqiyatli


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
