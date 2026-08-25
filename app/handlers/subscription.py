"""Obunani tekshirish callback'i."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import subscription_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.subscription_service import SubscriptionService
from app.utils.i18n import t

router = Router(name="subscription")


@router.callback_query(F.data == "check_subscription")
async def check_subscription(
    callback: CallbackQuery,
    lang: str,
    session: AsyncSession,
    redis: Redis,
) -> None:
    service = SubscriptionService(session, redis)
    unsubscribed = await service.get_unsubscribed(
        callback.bot, callback.from_user.id, force=True
    )

    if unsubscribed:
        await callback.answer(t("subscribe_fail", lang), show_alert=True)
        if callback.message is not None:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=subscription_keyboard(unsubscribed, lang)
                )
            except Exception:  # noqa: BLE001
                pass
        return

    await callback.answer(t("subscribe_ok", lang), show_alert=False)
    if callback.message is not None:
        try:
            await callback.message.delete()
        except Exception:  # noqa: BLE001
            pass
        await callback.message.answer(
            t("main_menu", lang), reply_markup=main_menu_keyboard(lang)
        )
