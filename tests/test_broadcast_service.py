"""Durable broadcast tizimi testlari.

Avvalgi dizayn (asyncio.Task + RAMdagi to'liq ro'yxat) o'rniga endi
DB-backed joblar. Shuning uchun tekshiriladigan narsalar ham o'zgardi:
  • xato klassifikatsiyasi (blocked / failed / retry);
  • batch-batch o'qish (butun auditoriya RAMga YUKLANMAYDI);
  • har batchdan keyin progress + kursor saqlanishi (restart-safe);
  • kursordan DAVOM ETISH (job yarmidan qayta boshlanmaydi);
  • admin bekor qilganda darhol to'xtash.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.methods import CopyMessage, SendMessage

from app.services.broadcast_service import _process_job, _send_one
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
    return lambda: _FakeSessionCtx(AsyncMock())


class _FakeUserRepo:
    """Keyset batch'larni simulyatsiya qiladi: (user_id, telegram_id)."""

    def __init__(self, recipients: list[tuple[int, int]]) -> None:
        self._recipients = recipients
        self.blocked_bulk_calls: list[list[int]] = []

    async def get_active_recipients_batch(
        self, after_user_id: int, limit: int
    ) -> list[tuple[int, int]]:
        rows = [r for r in self._recipients if r[0] > after_user_id]
        return rows[:limit]

    async def set_blocked_bulk(self, telegram_ids: list[int]) -> None:
        self.blocked_bulk_calls.append(list(telegram_ids))


class _FakeJobRepo:
    def __init__(self, status: str = "running") -> None:
        self._status = status
        self.progress_calls: list[dict] = []
        self.finished: list[tuple[int, str]] = []

    async def current_status(self, _job_id: int) -> str:
        return self._status

    async def save_progress(
        self, job_id: int, *, sent: int, blocked: int, failed: int, cursor: int
    ) -> None:
        self.progress_calls.append(
            {"job_id": job_id, "sent": sent, "blocked": blocked,
             "failed": failed, "cursor": cursor}
        )

    async def finish(self, job_id: int, status: str, error: str | None = None) -> None:
        self.finished.append((job_id, status))


def _telegram_side_effect(_bot, method, **_kwargs):  # noqa: ANN001
    """222 -> bloklagan, 333 -> chat not found (ham blocked), 444 -> xato."""
    if isinstance(method, CopyMessage):
        if method.chat_id == 222:
            raise TelegramForbiddenError(method=method, message="bot was blocked by the user")
        if method.chat_id == 333:
            raise TelegramBadRequest(method=method, message="chat not found")
        if method.chat_id == 444:
            raise TelegramBadRequest(method=method, message="message to copy not found")
        return None
    return None


async def _run_job(bot, user_repo, job_repo, *, cursor: int = 0) -> None:  # noqa: ANN001
    with patch(
        "app.services.broadcast_service.UserRepository", return_value=user_repo
    ), patch(
        "app.services.broadcast_service.BroadcastJobRepository", return_value=job_repo
    ), patch(
        "app.services.broadcast_service.asyncio.sleep", new=AsyncMock()
    ):
        await _process_job(
            bot,
            _session_factory(),
            1,
            from_chat_id=-100_999,
            message_id=5,
            admin_id=_ADMIN_ID,
            lang="uz",
            sent=0,
            blocked=0,
            failed=0,
            cursor=cursor,
        )


# === _send_one: xato klassifikatsiyasi ===

@pytest.mark.asyncio
async def test_send_one_success() -> None:
    bot = make_bot()
    bot.session.return_value = None
    assert await _send_one(bot, 111, -100_999, 5) == "sent"


@pytest.mark.asyncio
async def test_send_one_forbidden_is_blocked() -> None:
    bot = make_bot()
    bot.session.side_effect = _telegram_side_effect
    assert await _send_one(bot, 222, -100_999, 5) == "blocked"


@pytest.mark.asyncio
async def test_send_one_chat_not_found_is_blocked() -> None:
    """Hisob o'chirilgan — keyingi broadcastlarda behuda urinmaslik uchun."""
    bot = make_bot()
    bot.session.side_effect = _telegram_side_effect
    assert await _send_one(bot, 333, -100_999, 5) == "blocked"


@pytest.mark.asyncio
async def test_send_one_other_bad_request_is_failed() -> None:
    """Boshqa BadRequest — foydalanuvchi bloklagan degani EMAS."""
    bot = make_bot()
    bot.session.side_effect = _telegram_side_effect
    assert await _send_one(bot, 444, -100_999, 5) == "failed"


@pytest.mark.asyncio
async def test_send_one_retries_after_flood_wait() -> None:
    bot = make_bot()
    calls = {"n": 0}

    async def _side(_bot, method, **_kwargs):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise TelegramRetryAfter(method=method, message="flood", retry_after=0)
        return None

    bot.session.side_effect = _side
    with patch("app.services.broadcast_service.asyncio.sleep", new=AsyncMock()):
        assert await _send_one(bot, 111, -100_999, 5) == "sent"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_send_one_retries_network_error_then_fails() -> None:
    bot = make_bot()

    async def _side(_bot, method, **_kwargs):  # noqa: ANN001
        raise TelegramNetworkError(method=method, message="timeout")

    bot.session.side_effect = _side
    with patch("app.services.broadcast_service.asyncio.sleep", new=AsyncMock()):
        assert await _send_one(bot, 111, -100_999, 5) == "failed"


# === _process_job: batching, progress, resume, cancel ===

@pytest.mark.asyncio
async def test_process_job_counts_and_marks_blocked() -> None:
    bot = make_bot()
    bot.session.side_effect = _telegram_side_effect
    user_repo = _FakeUserRepo([(1, 111), (2, 222), (3, 333), (4, 444)])
    job_repo = _FakeJobRepo()

    await _run_job(bot, user_repo, job_repo)

    last = job_repo.progress_calls[-1]
    assert last["sent"] == 1  # 111
    assert last["blocked"] == 2  # 222 (forbidden) + 333 (chat not found)
    assert last["failed"] == 1  # 444
    # Bloklanganlar bazada belgilandi (keyingi broadcastda o'tkazib yuboriladi)
    assert user_repo.blocked_bulk_calls == [[222, 333]]
    assert job_repo.finished == [(1, "completed")]


@pytest.mark.asyncio
async def test_process_job_saves_cursor_for_restart_safety() -> None:
    """Kursor oxirgi ishlangan user.id ga teng bo'lishi kerak — restartda
    shu yerdan davom etadi."""
    bot = make_bot()
    bot.session.return_value = None
    user_repo = _FakeUserRepo([(10, 111), (20, 112), (30, 113)])
    job_repo = _FakeJobRepo()

    await _run_job(bot, user_repo, job_repo)

    assert job_repo.progress_calls[-1]["cursor"] == 30


@pytest.mark.asyncio
async def test_process_job_resumes_from_cursor_and_skips_done_users() -> None:
    """Restartdan keyin: kursor 20 bo'lsa, faqat 30 qolgani yuboriladi
    (birinchi ikkitasi QAYTA yuborilmaydi)."""
    bot = make_bot()
    bot.session.return_value = None
    user_repo = _FakeUserRepo([(10, 111), (20, 112), (30, 113)])
    job_repo = _FakeJobRepo()

    await _run_job(bot, user_repo, job_repo, cursor=20)

    copies = [
        c.args[1] for c in bot.session.await_args_list
        if isinstance(c.args[1], CopyMessage)
    ]
    assert [c.chat_id for c in copies] == [113]
    assert job_repo.progress_calls[-1]["sent"] == 1


@pytest.mark.asyncio
async def test_process_job_stops_when_admin_cancels() -> None:
    """Admin 'To'xtatish' bosgan — worker batch boshida darhol chiqadi."""
    bot = make_bot()
    bot.session.return_value = None
    user_repo = _FakeUserRepo([(1, 111), (2, 112)])
    job_repo = _FakeJobRepo(status="cancelled")

    await _run_job(bot, user_repo, job_repo)

    copies = [
        c.args[1] for c in bot.session.await_args_list
        if isinstance(c.args[1], CopyMessage)
    ]
    assert copies == []  # hech kimga yuborilmadi
    # 'cancelled' statusni qayta yozmaymiz (admin allaqachon o'rnatgan)
    assert job_repo.finished == []


@pytest.mark.asyncio
async def test_process_job_reports_to_admin_at_the_end() -> None:
    bot = make_bot()
    bot.session.side_effect = _telegram_side_effect
    user_repo = _FakeUserRepo([(1, 111)])
    job_repo = _FakeJobRepo()

    await _run_job(bot, user_repo, job_repo)

    reports = [
        c.args[1] for c in bot.session.await_args_list
        if isinstance(c.args[1], SendMessage) and c.args[1].chat_id == _ADMIN_ID
    ]
    assert len(reports) == 1
    assert "1" in reports[0].text


@pytest.mark.asyncio
async def test_process_job_does_not_load_all_recipients_at_once() -> None:
    """Batch chegarasi hurmat qilinadi — 100k+ auditoriyada RAM portlamasin."""
    bot = make_bot()
    bot.session.return_value = None
    recipients = [(i, 1000 + i) for i in range(1, 1201)]  # 1200 ta
    user_repo = _FakeUserRepo(recipients)
    job_repo = _FakeJobRepo()

    calls: list[int] = []
    original = user_repo.get_active_recipients_batch

    async def _tracked(after_user_id: int, limit: int):  # noqa: ANN202
        calls.append(limit)
        return await original(after_user_id, limit)

    user_repo.get_active_recipients_batch = _tracked  # type: ignore[method-assign]

    await _run_job(bot, user_repo, job_repo)

    assert calls, "batch o'qish umuman chaqirilmadi"
    assert all(limit <= 500 for limit in calls)
    # 1200 ta qabul qiluvchi -> kamida 3 ta batch (500+500+200) + bo'sh yakun
    assert len(calls) >= 3
    assert job_repo.progress_calls[-1]["sent"] == 1200
