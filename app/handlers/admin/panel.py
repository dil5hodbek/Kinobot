"""Admin panelga kirish/chiqish va umumiy /cancel."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.reply import admin_menu_keyboard, main_menu_keyboard
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

router = Router(name="admin_panel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def open_admin(message: Message, lang: str, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("admin_panel", lang), reply_markup=admin_menu_keyboard(lang))


@router.message(Command("cancel"))
async def cancel_any(message: Message, lang: str, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        t("action_cancelled", lang), reply_markup=admin_menu_keyboard(lang)
    )


@router.message(ButtonText("btn_exit"))
async def exit_admin(message: Message, lang: str, state: FSMContext) -> None:
    # Holat filtri yo'q — wizard o'rtasida ham chiqish ishlaydi.
    await state.clear()
    await message.answer(
        t("admin_exited", lang), reply_markup=main_menu_keyboard(lang)
    )
