"""Admin: majburiy obuna kanallarini dinamik boshqarish."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.reply import admin_menu_keyboard
from app.repositories.channel_repository import ChannelRepository
from app.states.admin_states import AddChannel
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="admin_channels")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


@router.message(StateFilter(None), ButtonText("btn_add_channel"))
async def start_add_channel(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    # Avval DB dagi kanallar ro'yxatini o'chirish tugmalari bilan ko'rsatamiz
    channels = await ChannelRepository(session).get_active()
    if channels:
        builder = InlineKeyboardBuilder()
        for ch in channels:
            builder.row(
                InlineKeyboardButton(
                    text=f"🗑 @{ch.channel_username}",
                    callback_data=f"chdel:{ch.id}",
                )
            )
        await message.answer(
            t("channel_list_admin_title", lang), reply_markup=builder.as_markup()
        )

    await state.set_state(AddChannel.waiting_username)
    await message.answer(t("channel_add_ask", lang))


@router.message(AddChannel.waiting_username)
async def got_channel(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    username = (message.text or "").strip().lstrip("@")
    if not username:
        await message.answer(t("channel_add_not_admin", lang))
        return

    bot: Bot = message.bot
    title, invite_link = await _verify_bot_admin(bot, username)
    if title is None:
        await message.answer(t("channel_add_not_admin", lang))
        return

    repo = ChannelRepository(session)
    if await repo.get_by_username(username) is not None:
        await message.answer(t("channel_add_exists", lang))
        await state.clear()
        await message.answer(
            t("admin_panel", lang), reply_markup=admin_menu_keyboard(lang)
        )
        return

    await repo.create(
        channel_username=username,
        channel_title=title,
        invite_link=invite_link,
    )
    await state.clear()
    await message.answer(
        t("channel_add_saved", lang, username=username),
        reply_markup=admin_menu_keyboard(lang),
    )


@router.callback_query(F.data.startswith("chdel:"))
async def remove_channel(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        channel_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    repo = ChannelRepository(session)
    channel = await repo.get_by_id(channel_id)
    if channel is not None:
        await repo.deactivate(channel_id)
    if callback.message is not None:
        await callback.message.answer(t("channel_removed", lang))


async def _verify_bot_admin(
    bot: Bot, username: str
) -> tuple[str | None, str | None]:
    """Bot kanalda admin ekanini tekshiradi. (title, invite_link) qaytaradi."""
    try:
        chat = await bot.get_chat(f"@{username}")
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status not in _ADMIN_STATUSES:
            return None, None
    except TelegramAPIError as exc:
        logger.warning("Kanal tekshiruvi xatosi (@%s): %s", username, exc)
        return None, None

    invite_link = chat.invite_link
    if invite_link is None:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except TelegramAPIError:
            invite_link = None

    return (chat.title or username), invite_link
