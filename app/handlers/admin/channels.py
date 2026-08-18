"""Admin: majburiy obuna kanallarini dinamik boshqarish."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.reply import admin_menu_keyboard
from app.services.audit_service import audit
from app.services.channel_service import AddChannelResult, ChannelService
from app.states.admin_states import AddChannel
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_channels")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(StateFilter(None), ButtonText("btn_add_channel"))
async def start_add_channel(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    # Avval DB dagi kanallar ro'yxatini o'chirish tugmalari bilan ko'rsatamiz
    channels = await ChannelService(session).list_active()
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
            t("channel_list_admin_title", lang, count=len(channels)),
            reply_markup=builder.as_markup(),
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
    outcome = await ChannelService(session).add_channel(bot, username)

    if outcome.result is AddChannelResult.NOT_ADMIN:
        await message.answer(t("channel_add_not_admin", lang))
        return

    if outcome.result is AddChannelResult.ALREADY_EXISTS:
        await message.answer(t("channel_add_exists", lang))
        await state.clear()
        await message.answer(
            t("admin_panel", lang), reply_markup=admin_menu_keyboard(lang)
        )
        return

    if message.from_user is not None:
        await audit(
            session,
            admin_id=message.from_user.id,
            action="channel_add",
            entity_type="channel",
            entity_id=username,
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

    await ChannelService(session).remove_channel(channel_id)
    await audit(
        session,
        admin_id=callback.from_user.id,
        action="channel_remove",
        entity_type="channel",
        entity_id=channel_id,
    )
    if callback.message is not None:
        await callback.message.answer(t("channel_removed", lang))
