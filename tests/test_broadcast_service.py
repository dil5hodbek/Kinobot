"""BroadcastService._run_broadcast() testlari.

Tekshiriladi: bloklagan foydalanuvchi (TelegramForbiddenError) to'g'ri
aniqlanadi va is_blocked=True qilib belgilanadi (keyingi broadcast'larda
unga behuda urinilmasin), muvaffaqiyatli/muvaffaqiyatsiz yuborishlar
alohida hisoblanadi, va yakunda adminga hisobot yuboriladi.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import CopyMessage, SendMessage

from app.services.broadcast_service import _run_broadcast
from tests.helpers import make_bot

_ADMIN_ID = 900_900


class _FakeSessionCtx:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


def _session_factory():
    return lambda: _FakeSessionCtx(AsyncMock())  # session.commit() shu yerda kerak


def _session_side_effect(_bot: object, method: object, timeout: float | None = None):
    if isinstance(method, CopyMessage):
        if method.chat_id == 222:
            raise TelegramForbiddenError(method=method, message="bot was blocked by the user")
        if method.chat_id == 333:
            raise TelegramBadRequest(method=method, message="chat not found")
        return None  # 111 uchun muvaffaqiyatli
    if isinstance(method, SendMessage):
        return None  # admin hisobot xabari muvaffaqiyatli
    return None


@pytest.mark.asyncio
async def test_broadcast_detects_blocked_and_reports() -> None:
    bot = make_bot()
    bot.session.side_effect = _session_side_effect

    fake_repo = AsyncMock()
    fake_repo.get_active_telegram_ids.return_value = [111, 222, 333]

    with patch(
        "app.services.broadcast_service.UserRepository", return_value=fake_repo
    ):
        await _run_broadcast(
            bot,
            _session_factory(),
            from_chat_id=-100_999,
            message_id=5,
            admin_id=_ADMIN_ID,
            lang="uz",
        )

    # Faqat 222 (Forbidden) bloklangan deb belgilanishi kerak — 333
    # (boshqa xato) emas.
    fake_repo.set_blocked_bulk.assert_awaited_once_with([222])

    # Admin hisobot oldi.
    report_calls = [
        call.args[1]
        for call in bot.session.await_args_list
        if isinstance(call.args[1], SendMessage) and call.args[1].chat_id == _ADMIN_ID
    ]
    assert len(report_calls) == 1
    assert "1" in report_calls[0].text  # sent=1 hisobotda ko'rinadi


@pytest.mark.asyncio
async def test_broadcast_paces_sends_below_telegram_limit() -> None:
    """Har yuborishdan keyin sleep bo'lishi kerak — Telegram limitiga tegib qolmasin."""
    bot = make_bot()
    bot.session.side_effect = _session_side_effect

    fake_repo = AsyncMock()
    fake_repo.get_active_telegram_ids.return_value = [111]

    with patch(
        "app.services.broadcast_service.UserRepository", return_value=fake_repo
    ), patch(
        "app.services.broadcast_service.asyncio.sleep", new=AsyncMock()
    ) as sleep_mock:
        await _run_broadcast(
            bot,
            _session_factory(),
            from_chat_id=-100_999,
            message_id=5,
            admin_id=_ADMIN_ID,
            lang="uz",
        )

    assert sleep_mock.await_count >= 1  # pacing chaqirildi
    fake_repo.set_blocked_bulk.assert_not_awaited()  # hech kim bloklanmagan


@pytest.mark.asyncio
async def test_cancellation_mid_broadcast_still_flushes_blocked() -> None:
    """Bot to'xtatilsa (task.cancel()) — hozirgacha bloklanganlar YO'QOLMASLIGI kerak.

    finally-blok (task 8 tuzatishi) buni kafolatlaydi: CancelledError sikl
    ichida chiqsa ham, flush_blocked() baribir bajariladi.
    """
    bot = make_bot()
    bot.session.side_effect = _session_side_effect  # 222 -> Forbidden (blocked)

    fake_repo = AsyncMock()
    fake_repo.get_active_telegram_ids.return_value = [222, 333]

    call_count = 0

    async def _sleep_then_cancel(_seconds: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.CancelledError()

    with patch(
        "app.services.broadcast_service.UserRepository", return_value=fake_repo
    ), patch(
        "app.services.broadcast_service.asyncio.sleep", new=_sleep_then_cancel
    ):
        with pytest.raises(asyncio.CancelledError):
            await _run_broadcast(
                bot,
                _session_factory(),
                from_chat_id=-100_999,
                message_id=5,
                admin_id=_ADMIN_ID,
                lang="uz",
            )

    # 222 birinchi bo'lib bloklandi (Forbidden), keyin sleep() bekor qildi —
    # baribir flush qilingan bo'lishi kerak.
    fake_repo.set_blocked_bulk.assert_awaited_once_with([222])
