"""AdminMenuInterruptMiddleware testlari.

Bug: admin biror FSM oqimida (masalan "Tahrirlash" kodni kutayotganda) boshqa
menyu tugmasini bossa, matn eski oqimga tushib ketardi va yangi oqim hech
qachon boshlanmasdi. Middleware buni oldini olishi kerak: menyu tugmasi matni
kelsa, admin FSM holatini routerlar ko'rishidan oldin tozalaydi.

MUHIM: `StateFilter` joriy holatni `state.get_state()` orqali JONLI emas,
balki `data["raw_state"]` degan OLDINDAN olingan snapshot orqali tekshiradi
(`aiogram/filters/state.py`). Shuning uchun middleware faqat `state.clear()`
chaqirishi YETARLI EMAS — `data["raw_state"]`ni ham qo'lda `None`ga
o'rnatishi shart, aks holda filtrlar hamon eski holatni ko'radi (bu aynan
production'da ushlangan haqiqiy regressiya edi — quyidagi testlar buni
maxsus tekshiradi).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.middlewares.admin_menu_interrupt import AdminMenuInterruptMiddleware
from app.utils.i18n import t
from tests.helpers import make_bot, make_message


class _FakeState:
    def __init__(self, initial: str | None) -> None:
        self._state = initial
        self.clear_calls = 0

    async def get_state(self) -> str | None:
        return self._state

    async def clear(self) -> None:
        self.clear_calls += 1
        self._state = None


def _data(message, state, raw_state) -> dict:  # noqa: ANN001
    return {"event_from_user": message.from_user, "state": state, "raw_state": raw_state}


@pytest.mark.asyncio
async def test_menu_button_clears_active_admin_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_add_movie", "uz"))
    state = _FakeState("EditMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    data = _data(message, state, "EditMovie:waiting_code")
    result = await middleware(handler, message, data)

    assert result == "ok"
    assert state.clear_calls == 1
    # Filtrlar aynan shu kalitdan o'qiydi — shu tozalanmasa, tuzatish ishlamaydi.
    assert data["raw_state"] is None
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_button_text_does_not_clear_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text="777")
    state = _FakeState("EditMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    data = _data(message, state, "EditMovie:waiting_code")
    await middleware(handler, message, data)

    assert state.clear_calls == 0
    assert data["raw_state"] == "EditMovie:waiting_code"


@pytest.mark.asyncio
async def test_non_admin_button_text_does_not_clear_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    message = make_message(bot, 999_999_999, text=t("btn_add_movie", "uz"))
    state = _FakeState("SomeState:waiting")
    handler = AsyncMock(return_value="ok")

    data = _data(message, state, "SomeState:waiting")
    await middleware(handler, message, data)

    assert state.clear_calls == 0
    assert data["raw_state"] == "SomeState:waiting"


@pytest.mark.asyncio
async def test_already_no_state_is_a_no_op() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_edit_movie", "uz"))
    state = _FakeState(None)
    handler = AsyncMock(return_value="ok")

    data = _data(message, state, None)
    await middleware(handler, message, data)

    assert state.clear_calls == 0


@pytest.mark.asyncio
async def test_button_label_from_any_language_clears_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_delete_movie", "ru"))
    state = _FakeState("AddMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    data = _data(message, state, "AddMovie:waiting_code")
    await middleware(handler, message, data)

    assert state.clear_calls == 1
    assert data["raw_state"] is None
