"""'🧹 Suhbatni tozalash' — HAQIQIY aiogram Dispatcher.feed_update() orqali
integratsion test.

Ilgari admin_menu_interrupt bug'ida ko'rganimizdek, izolyatsiyadagi
middleware/handler testlari aiogram'ning haqiqiy routing (filtr + middleware
tartibi) xatolarini qamrab olmasligi mumkin. Shu sabab bu yerda HAQIQIY
router + Dispatcher + feed_update() bilan to'liq oqim tekshiriladi: tugma
matni -> tasdiqlash so'rovi -> "Ha" callback -> xabarlar o'chirilishi.
"""
from __future__ import annotations

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import DeleteMessage, DeleteMessages, SendMessage
from aiogram.types import Update

from app.handlers.clear_chat import router as clear_chat_router
from app.middlewares.message_log import MessageLogMiddleware
from app.services.chat_cleanup_service import log_message
from app.utils.i18n import t
from tests.helpers import FakeZSetRedis, make_bot, make_callback, make_message


def _build_dispatcher(redis: FakeZSetRedis) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp["redis"] = redis
    # Production'da UserContextMiddleware `lang`ni bazadan o'rnatadi — bu
    # minimal testda DB kerak emasligi uchun to'g'ridan-to'g'ri beramiz.
    dp["lang"] = "uz"
    dp.message.outer_middleware(MessageLogMiddleware(redis))
    # `clear_chat_router` — production'dagi modul-darajasidagi SINGLETON
    # (boshqa barcha handler modullari kabi). aiogram bir Router'ni ikki marta
    # `include_router` qilishga yo'l qo'ymaydi, lekin har bir test o'z
    # Dispatcher'ini yasaydi — shuning uchun avvalgi test qoldirgan
    # bog'lanishni shu yerda qo'lda uzib qo'yamiz (faqat testlar uchun).
    clear_chat_router._parent_router = None  # noqa: SLF001
    dp.include_router(clear_chat_router)
    return dp


@pytest.mark.asyncio
async def test_button_press_shows_confirmation_end_to_end() -> None:
    redis = FakeZSetRedis()
    dp = _build_dispatcher(redis)
    bot = make_bot()
    bot.session.return_value = None

    chat_id = 42
    text_msg = make_message(bot, chat_id, text=t("btn_clear_chat", "uz"))
    update = Update.model_construct(update_id=1, message=text_msg)

    await dp.feed_update(bot, update)

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    datas = {btn.callback_data for row in method.reply_markup.inline_keyboard for btn in row}
    assert "clearchat_confirm" in datas


@pytest.mark.asyncio
async def test_confirm_callback_deletes_tracked_messages_end_to_end() -> None:
    redis = FakeZSetRedis()
    dp = _build_dispatcher(redis)
    bot = make_bot()
    chat_id = 43

    # Oldindan "tarix"da bo'lgan xabarlar (masalan foydalanuvchi va bot
    # o'rtasidagi avvalgi almashuv).
    await log_message(redis, chat_id, 100)
    await log_message(redis, chat_id, 101)

    bot.session.return_value = True
    callback = make_callback(bot, chat_id, data="clearchat_confirm", chat_id=chat_id)
    update = Update.model_construct(update_id=2, callback_query=callback)

    await dp.feed_update(bot, update)

    delete_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], DeleteMessages)
    ]
    deleted_ids = {mid for c in delete_calls for mid in c.args[1].message_ids}
    assert {100, 101}.issubset(deleted_ids)

    send_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], SendMessage)
    ]
    assert len(send_calls) == 1


@pytest.mark.asyncio
async def test_cancel_callback_removes_prompt_end_to_end() -> None:
    redis = FakeZSetRedis()
    dp = _build_dispatcher(redis)
    bot = make_bot()
    bot.session.return_value = True

    callback = make_callback(bot, 1, data="clearchat_cancel", chat_id=44)
    update = Update.model_construct(update_id=3, callback_query=callback)

    await dp.feed_update(bot, update)

    delete_calls = [
        c for c in bot.session.call_args_list if isinstance(c.args[1], DeleteMessage)
    ]
    assert len(delete_calls) == 1
