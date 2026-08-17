"""Til tanlash callback'lari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import language_keyboard, subscription_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.utils.filters import ButtonText
from app.utils.i18n import SUPPORTED_LANGUAGES, t

router = Router(name="language")


@router.message(ButtonText("btn_language"))
async def change_language(message: Message, lang: str) -> None:
    """Menyudan tilni qayta tanlash."""
    await message.answer(t("start_choose_lang", lang), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(
    callback: CallbackQuery,
    session: AsyncSession,
    redis: Redis,
) -> None:
    new_lang = (callback.data or "").split(":", 1)[1]
    if new_lang not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return

    user_service = UserService(session)
    await user_service.set_language(callback.from_user.id, new_lang)

    await callback.answer()
    if callback.message is not None:
        try:
            await callback.message.edit_text(t("lang_saved", new_lang))
        except Exception:  # noqa: BLE001 - matn o'zgarmagan bo'lishi mumkin
            pass

    # Til tanlangach — obunani tekshiramiz
    sub_service = SubscriptionService(session, redis)
    unsubscribed = await sub_service.get_unsubscribed(callback.bot, callback.from_user.id)

    target = callback.message
    if target is None:
        return

    if unsubscribed:
        await target.answer(
            t("subscribe_required", new_lang),
            reply_markup=subscription_keyboard(unsubscribed, new_lang),
        )
    else:
        await target.answer(
            t("main_menu", new_lang), reply_markup=main_menu_keyboard(new_lang)
        )
