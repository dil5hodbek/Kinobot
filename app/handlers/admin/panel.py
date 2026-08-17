"""Admin panelga kirish/chiqish, 2 qavatli menyu navigatsiyasi va /cancel.

Admin menyusi HUB + 2 submenu (reply.py'даgi izohga qarang). Navigatsiya
tugmalari (Kinolar/Boshqaruv/Orqaga/Oddiy menyu) hech qanday biznes
amalini bajarmaydi — faqat reply-klaviaturani almashtiradi. Mavjud
amal-tugmalarning (btn_add_movie va h.k.) BIRONTASI o'zgarmagan.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.reply import (
    admin_management_menu_keyboard,
    admin_menu_keyboard,
    admin_movies_menu_keyboard,
    main_menu_keyboard,
)
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


@router.message(StateFilter(None), ButtonText("btn_movies_menu"))
async def open_movies_menu(message: Message, lang: str) -> None:
    await message.answer(
        t("admin_panel", lang), reply_markup=admin_movies_menu_keyboard(lang)
    )


@router.message(StateFilter(None), ButtonText("btn_management_menu"))
async def open_management_menu(message: Message, lang: str) -> None:
    await message.answer(
        t("admin_panel", lang), reply_markup=admin_management_menu_keyboard(lang)
    )


@router.message(StateFilter(None), ButtonText("btn_back"))
async def back_to_hub(message: Message, lang: str) -> None:
    await message.answer(t("admin_panel", lang), reply_markup=admin_menu_keyboard(lang))


@router.message(StateFilter(None), ButtonText("btn_user_menu"))
async def open_user_menu(message: Message, lang: str) -> None:
    # "Chiqish"dan farqli — admin hisobi/holati o'zgarmaydi, faqat
    # oddiy foydalanuvchi ko'radigan menyu ko'rsatiladi (/admin bilan
    # istalgan payt qaytish mumkin).
    await message.answer(t("main_menu", lang), reply_markup=main_menu_keyboard(lang))
