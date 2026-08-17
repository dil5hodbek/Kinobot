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
    service = SubscriptionService(session, redis)
    channels = await service.list_channels()

    if not channels:
        await message.answer(t("channels_empty", lang))
        return

    await message.answer(
        t("channels_list_title", lang),
        reply_markup=channels_list_keyboard(channels),
    )
