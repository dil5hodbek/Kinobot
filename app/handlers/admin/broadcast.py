"""Admin: reklama / ommaviy xabar (broadcast) FSM oqimi.

Broadcast endi DURABLE: tasdiqlangach DB'da job yaratiladi, uni alohida
worker (app/services/broadcast_service.py) oladi. Bot restart bo'lsa ham
job yo'qolmaydi. Admin "⛔ To'xtatish" tugmasi bilan istalgan payt bekor
qila oladi.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import broadcast_confirm_keyboard
from app.keyboards.reply import admin_menu_keyboard
from app.services.audit_service import audit
from app.services.broadcast_service import BroadcastService
from app.states.admin_states import Broadcast
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _cancel_keyboard(job_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_broadcast_cancel_job", lang),
                    callback_data=f"bccancel:{job_id}",
                )
            ]
        ]
    )


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
    session: AsyncSession,
) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    service = BroadcastService(session)
    job_id = await service.create_job(
        created_by=callback.from_user.id,
        from_chat_id=data["from_chat_id"],
        message_id=data["message_id"],
        lang=lang,
    )
    await audit(
        session,
        admin_id=callback.from_user.id,
        action="broadcast_start",
        entity_type="broadcast",
        entity_id=job_id,
    )

    if callback.message is not None:
        await callback.message.answer(
            t("broadcast_started", lang),
            reply_markup=_cancel_keyboard(job_id, lang),
        )
        await callback.message.answer(
            t("admin_panel", lang), reply_markup=admin_menu_keyboard(lang)
        )


@router.callback_query(F.data.startswith("bccancel:"))
async def cancel_running_broadcast(
    callback: CallbackQuery, lang: str, session: AsyncSession
) -> None:
    await callback.answer()
    try:
        job_id = int((callback.data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return

    cancelled = await BroadcastService(session).cancel_job(job_id)
    if cancelled:
        await audit(
            session,
            admin_id=callback.from_user.id,
            action="broadcast_cancel",
            entity_type="broadcast",
            entity_id=job_id,
        )
    if callback.message is not None:
        key = "broadcast_job_cancelled" if cancelled else "broadcast_cancel_too_late"
        await callback.message.answer(t(key, lang))


@router.callback_query(Broadcast.waiting_confirm, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, lang: str, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            t("action_cancelled", lang), reply_markup=admin_menu_keyboard(lang)
        )
