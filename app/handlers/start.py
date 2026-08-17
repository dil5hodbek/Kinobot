"""/start va /help komandalari."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.inline import language_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.models.user import User
from app.services.subscription_service import SubscriptionService
from app.keyboards.inline import subscription_keyboard
from app.utils.i18n import t

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user: User,
    lang: str,
    is_new_user: bool,
    session: AsyncSession,
    redis: Redis,
    state: FSMContext,
) -> None:
    await state.clear()

    if is_new_user:
        # Yangi foydalanuvchi — avval til tanlaydi
        await message.answer(t("start_choose_lang", lang), reply_markup=language_keyboard())
        return

    # Mavjud foydalanuvchi — obunani tekshiramiz
    service = SubscriptionService(session, redis)
    unsubscribed = await service.get_unsubscribed(message.bot, message.from_user.id)
    if unsubscribed:
        await message.answer(
            t("subscribe_required", lang),
            reply_markup=subscription_keyboard(unsubscribed, lang),
        )
        return

    await message.answer(t("main_menu", lang), reply_markup=main_menu_keyboard(lang))


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str) -> None:
    await message.answer(t("help", lang, admin_phone=settings.admin_phone))
