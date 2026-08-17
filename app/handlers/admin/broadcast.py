"""Admin: reklama / ommaviy xabar (broadcast) FSM oqimi."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.keyboards.inline import broadcast_confirm_keyboard
from app.keyboards.reply import admin_menu_keyboard
from app.services.broadcast_service import BroadcastService, start_broadcast_job
from app.states.admin_states import Broadcast
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(StateFilter(None), ButtonText("btn_broadcast"))
async def start_broadcast(message: Message, lang: str, state: FSMContext) -> None:
    await state.set_state(Broadcast.waiting_message)
    await message.answer(t("broadcast_ask", lang))


@router.message(Broadcast.waiting_message)
async def got_message(
    message: Message, lang: str, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    count = await BroadcastService(session).count_recipients()
    await state.set_state(Broadcast.waiting_confirm)
    await message.answer(
        t("broadcast_confirm", lang, count=count),
        reply_markup=broadcast_confirm_keyboard(lang),
    )


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_send")
async def do_broadcast(
    callback: CallbackQuery,
    lang: str,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    # Reklamani FON vazifasi sifatida ishga tushiramiz — handler bloklanmaydi.
    start_broadcast_job(
        callback.bot,
        session_factory,
        from_chat_id=data["from_chat_id"],
        message_id=data["message_id"],
        admin_id=callback.from_user.id,
        lang=lang,
    )

    if callback.message is not None:
        await callback.message.answer(
            t("broadcast_started", lang), reply_markup=admin_menu_keyboard(lang)
        )


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            t("action_cancelled", lang), reply_markup=admin_menu_keyboard(lang)
        )
