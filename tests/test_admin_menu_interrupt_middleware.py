"""AdminMenuInterruptMiddleware testlari.

Bug: admin biror FSM oqimida (masalan "Tahrirlash" kodni kutayotganda) boshqa
menyu tugmasini bossa, matn eski oqimga tushib ketardi va yangi oqim hech
qachon boshlanmasdi. Middleware buni oldini olishi kerak: menyu tugmasi matni
kelsa, admin FSM holatini routerlar ko'rishidan oldin tozalaydi.
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


def _data(message, state) -> dict:  # noqa: ANN001
    return {"event_from_user": message.from_user, "state": state}


@pytest.mark.asyncio
async def test_menu_button_clears_active_admin_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_add_movie", "uz"))
    state = _FakeState("EditMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    result = await middleware(handler, message, _data(message, state))

    assert result == "ok"
    assert state.clear_calls == 1
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_button_text_does_not_clear_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text="777")
    state = _FakeState("EditMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, _data(message, state))

    assert state.clear_calls == 0


@pytest.mark.asyncio
async def test_non_admin_button_text_does_not_clear_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    message = make_message(bot, 999_999_999, text=t("btn_add_movie", "uz"))
    state = _FakeState("SomeState:waiting")
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, _data(message, state))

    assert state.clear_calls == 0


@pytest.mark.asyncio
async def test_already_no_state_is_a_no_op() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_edit_movie", "uz"))
    state = _FakeState(None)
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, _data(message, state))

    assert state.clear_calls == 0


@pytest.mark.asyncio
async def test_button_label_from_any_language_clears_state() -> None:
    middleware = AdminMenuInterruptMiddleware()
    bot = make_bot()
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text=t("btn_delete_movie", "ru"))
    state = _FakeState("AddMovie:waiting_code")
    handler = AsyncMock(return_value="ok")

    await middleware(handler, message, _data(message, state))

    assert state.clear_calls == 1
