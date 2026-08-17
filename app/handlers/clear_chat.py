"""Foydalanuvchi: '🧹 Suhbatni tozalash' — so'nggi 48 soatlik chat tarixini o'chirish.

Telegram Bot API 48 soatdan eski xabarlarni o'chirishga umuman ruxsat
bermaydi — shuning uchun bu funksiya faqat SHU OYNADAGI xabarlarni
tozalaydi (app/services/chat_cleanup_service.py'dagi izohga qarang).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

from app.keyboards.inline import clear_chat_confirm_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.chat_cleanup_service import delete_messages, pop_recent_message_ids
from app.utils.filters import ButtonText
from app.utils.i18n import t

router = Router(name="clear_chat")


@router.message(ButtonText("btn_clear_chat"))
async def ask_clear_chat(message: Message, lang: str) -> None:
    await message.answer(
        t("clear_chat_confirm", lang),
        reply_markup=clear_chat_confirm_keyboard(lang),
    )


@router.callback_query(F.data == "clearchat_confirm")
async def do_clear_chat(callback: CallbackQuery, lang: str, redis: Redis) -> None:
    await callback.answer()
    if callback.message is None:
        return
    chat_id = callback.message.chat.id

    message_ids = await pop_recent_message_ids(redis, chat_id)
    deleted = await delete_messages(callback.bot, chat_id, message_ids)

    text = t("clear_chat_done", lang, count=deleted) if deleted else t("clear_chat_none", lang)
    await callback.bot.send_message(chat_id, text, reply_markup=main_menu_keyboard(lang))


@router.callback_query(F.data == "clearchat_cancel")
async def cancel_clear_chat(callback: CallbackQuery, lang: str) -> None:
    await callback.answer(t("clear_chat_cancelled", lang))
    if callback.message is None:
        return
    try:
        await callback.message.delete()
    except TelegramAPIError:
        pass
