"""Admin menyu tugmasi bosilganda joriy FSM oqimini bekor qiladi.

Muammo: har bir admin FSM oqimi o'z "kutish" qadamida ixtiyoriy matnni qabul
qiladi (masalan "Tahrirlash uchun kino kodini kiriting"). Admin shu payt
boshqa menyu tugmasini (masalan "➕ Kino qo'shish") bossa, matn baribir eski
oqimning kutayotgan qadamiga tushib, tugma nomi "kod" sifatida qidirilardi —
yangi oqim boshlanmasdi, birinchi tugma "yutib" olardi.

Yechim: xabar matni ma'lum menyu tugmalaridan biriga aynan teng bo'lsa, FSM
holati routerlar filtrlarni tekshirishidan OLDIN tozalanadi — shundan keyin
tegishli oqimning `StateFilter(None)` bilan himoyalangan kirish nuqtasi
o'zgarishsiz, normal ishga tushadi (btn_exit uchun ilgari qo'llangan
"holat filtrisiz chiqish" naqshi bilan bir xil g'oya, endi barcha menyu
tugmalariga umumlashtirilgan).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject
from aiogram.types import User as TgUser

from app.config import settings
from app.utils.i18n import all_labels

# Admin reply-klaviaturasidagi BARCHA menyu/navigatsiya/oqim-boshlovchi
# tugmalar — har biri bosilganda joriy oqim "yutib olmasligi" kerak.
_MENU_BUTTON_KEYS = (
    "btn_movies_menu",
    "btn_management_menu",
    "btn_back",
    "btn_user_menu",
    "btn_exit",
    "btn_add_movie",
    "btn_add_link_movie",
    "btn_edit_movie",
    "btn_delete_movie",
    "btn_codes",
    "btn_stats",
    "btn_broadcast",
    "btn_add_channel",
)


@lru_cache(maxsize=1)
def _menu_button_labels() -> frozenset[str]:
    labels: set[str] = set()
    for key in _MENU_BUTTON_KEYS:
        labels |= all_labels(key)
    return frozenset(labels)


class AdminMenuInterruptMiddleware(BaseMiddleware):
    """Admin menyu tugmasi kelsa — routerlardan oldin FSM holatini tozalaydi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text in _menu_button_labels():
            tg_user: TgUser | None = data.get("event_from_user")
            state: FSMContext | None = data.get("state")
            if (
                tg_user is not None
                and tg_user.id in settings.admin_ids
                and state is not None
                and await state.get_state() is not None
            ):
                await state.clear()
        return await handler(event, data)
