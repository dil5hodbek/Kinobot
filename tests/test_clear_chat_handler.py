"""app/handlers/clear_chat.py testlari."""
from __future__ import annotations

import pytest
from aiogram.methods import DeleteMessage, SendMessage

from app.handlers.clear_chat import ask_clear_chat, cancel_clear_chat, do_clear_chat
from app.services.chat_cleanup_service import log_message
from tests.helpers import FakeZSetRedis, make_bot, make_callback, make_message


@pytest.mark.asyncio
async def test_ask_clear_chat_shows_confirmation_keyboard() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="🧹 Suhbatni tozalash")

    await ask_clear_chat(message, lang="uz")

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert "48 soat" in method.text
    datas = {btn.callback_data for row in method.reply_markup.inline_keyboard for btn in row}
    assert datas == {"clearchat_confirm", "clearchat_cancel"}


@pytest.mark.asyncio
async def test_do_clear_chat_deletes_tracked_messages_and_reports_count() -> None:
    bot = make_bot()
    bot.session.return_value = True
    chat_id = 555
    callback = make_callback(bot, 1, data="clearchat_confirm", chat_id=chat_id)

    redis = FakeZSetRedis()
    await log_message(redis, chat_id, 10)
    await log_message(redis, chat_id, 11)
    await log_message(redis, chat_id, 12)

    await do_clear_chat(callback, lang="uz", redis=redis)

    delete_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], DeleteMessage)
    ]
    assert len(delete_calls) == 3
    assert {c.args[1].message_id for c in delete_calls} == {10, 11, 12}

    send_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], SendMessage)
    ]
    assert len(send_calls) == 1
    assert "3" in send_calls[0].args[1].text


@pytest.mark.asyncio
async def test_do_clear_chat_with_nothing_tracked_reports_none() -> None:
    bot = make_bot()
    bot.session.return_value = True
    chat_id = 556
    callback = make_callback(bot, 1, data="clearchat_confirm", chat_id=chat_id)
    redis = FakeZSetRedis()

    await do_clear_chat(callback, lang="uz", redis=redis)

    delete_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], DeleteMessage)
    ]
    send_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], SendMessage)
    ]
    assert delete_calls == []
    assert len(send_calls) == 1
    assert "O'chiriladigan" in send_calls[0].args[1].text


@pytest.mark.asyncio
async def test_cancel_clear_chat_deletes_prompt_message() -> None:
    bot = make_bot()
    bot.session.return_value = True
    callback = make_callback(bot, 1, data="clearchat_cancel", chat_id=557)

    await cancel_clear_chat(callback, lang="uz")

    delete_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], DeleteMessage)
    ]
    assert len(delete_calls) == 1
