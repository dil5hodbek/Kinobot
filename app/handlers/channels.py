"""Foydalanuvchi uchun 'Kanallar' tugmasi."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import channels_list_keyboard
from app.services.subscription_service import SubscriptionService
from app.utils.filters import ButtonText
from app.utils.i18n import t

router = Router(name="channels")


@router.message(ButtonText("btn_channels"))
async def show_channels(
    message: Message,
    lang: str,
    session: AsyncSession,
    redis: Redis,
) -> None:
    if message.from_user is None:
        return

    service = SubscriptionService(session, redis)
    channels_status = await service.channels_with_status(message.bot, message.from_user.id)

    if not channels_status:
        await message.answer(t("channels_empty", lang))
        return

    await message.answer(
        t("channels_list_title", lang),
        reply_markup=channels_list_keyboard(channels_status),
    )
