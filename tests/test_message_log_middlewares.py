"""MessageLogMiddleware (kiruvchi) va MessageLogSessionMiddleware (chiquvchi) testlari."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.methods import DeleteMessage, GetMe, SendMessage
from aiogram.types import Message as TgMessage

from app.middlewares.message_log import MessageLogMiddleware
from app.middlewares.message_log_session import MessageLogSessionMiddleware
from app.services.chat_cleanup_service import pop_recent_message_ids
from tests.helpers import FakeZSetRedis, make_bot, make_message


@pytest.mark.asyncio
async def test_incoming_message_gets_logged() -> None:
    redis = FakeZSetRedis()
    middleware = MessageLogMiddleware(redis)
    bot = make_bot()
    message = make_message(bot, 1, chat_id=777)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, {})

    assert result == "ok"
    handler.assert_awaited_once()
    ids = await pop_recent_message_ids(redis, 777)
    assert ids == [message.message_id]


@pytest.mark.asyncio
async def test_non_message_event_is_ignored() -> None:
    redis = FakeZSetRedis()
    middleware = MessageLogMiddleware(redis)
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, object(), {})

    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_middleware_logs_sent_message() -> None:
    redis = FakeZSetRedis()
    middleware = MessageLogSessionMiddleware(redis)
    bot = make_bot()
    method = SendMessage(chat_id=999, text="salom")
    sent = TgMessage.model_construct(message_id=42, date=None, chat=None)

    make_request = AsyncMock(return_value=sent)
    result = await middleware(make_request, bot, method)

    assert result is sent
    ids = await pop_recent_message_ids(redis, 999)
    assert ids == [42]


@pytest.mark.asyncio
async def test_session_middleware_ignores_results_without_message_id() -> None:
    """masalan DeleteMessage `bool` qaytaradi — kuzatuvga tegishli emas."""
    redis = FakeZSetRedis()
    middleware = MessageLogSessionMiddleware(redis)
    bot = make_bot()
    method = DeleteMessage(chat_id=999, message_id=1)

    make_request = AsyncMock(return_value=True)
    result = await middleware(make_request, bot, method)

    assert result is True
    ids = await pop_recent_message_ids(redis, 999)
    assert ids == []


@pytest.mark.asyncio
async def test_session_middleware_ignores_methods_without_chat_id() -> None:
    """masalan GetMe'da chat_id umuman yo'q."""
    redis = FakeZSetRedis()
    middleware = MessageLogSessionMiddleware(redis)
    bot = make_bot()
    method = GetMe()

    make_request = AsyncMock(return_value=object())
    result = await middleware(make_request, bot, method)

    assert make_request.await_count == 1
    assert result is not None
