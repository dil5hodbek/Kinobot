"""MovieService.deliver() testlari — ENG YUQORI USTUVORLIK.

Bu spec 10.6 ning aynan o'zi: video yuborib bo'lmasa (kanal postini
o'chirilgan/bot huquqi yo'q), kino FAOLSIZLANTIRILISHI va adminlarga
xabar berilishi shart — aks holda o'sha kino keyingi HAR BIR foydalanuvchi
uchun abadiy "topilmadi/xato" bo'lib qolaveradi, hech kim buni bilmaydi.
Muvaffaqiyatli yuborishda esa ko'rish statistikasi (views_count + tarix)
oshishi kerak — aks holda trend/statistika hech qachon to'g'ri bo'lmaydi.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import CopyMessage

from app.models.movie import Movie
from app.services.movie_service import MovieDeliveryError, MovieService
from tests.helpers import make_bot


class _FakeMovieRepo:
    def __init__(self) -> None:
        self.deactivated_ids: list[int] = []
        self.incremented_ids: list[int] = []
        self.views_added: list[tuple[int, int]] = []

    async def deactivate(self, movie_id: int) -> None:
        self.deactivated_ids.append(movie_id)

    async def increment_views(self, movie_id: int) -> None:
        self.incremented_ids.append(movie_id)

    async def add_view(self, user_db_id: int, movie_id: int) -> None:
        self.views_added.append((user_db_id, movie_id))


def _movie(movie_id: int = 7) -> Movie:
    return Movie(
        id=movie_id,
        code="777",
        channel_id=-100123,
        message_id=42,
        title_uz="Test Kino",
        title_ru=None,
        title_en=None,
        year=2024,
        genre="drama",
        views_count=5,
        is_active=True,
    )


def _service_with_fake_repo() -> tuple[MovieService, _FakeMovieRepo]:
    # session=None — deliver() sessiyani to'g'ridan-to'g'ri ishlatmaydi,
    # faqat self._repo orqali (uni fake bilan almashtiramiz).
    service = MovieService(session=None)  # type: ignore[arg-type]
    fake_repo = _FakeMovieRepo()
    service._repo = fake_repo  # type: ignore[attr-defined]
    return service, fake_repo


@pytest.mark.asyncio
async def test_successful_delivery_increments_views() -> None:
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    bot.session.return_value = None  # copy_message muvaffaqiyatli
    movie = _movie()

    await service.deliver(bot, movie, user_db_id=99, chat_id=555, lang="uz")

    assert repo.incremented_ids == [movie.id]
    assert repo.views_added == [(99, movie.id)]
    assert repo.deactivated_ids == []  # muvaffaqiyatда faolsizlantirilmaydi


@pytest.mark.asyncio
async def test_successful_delivery_uses_copy_message_not_forward() -> None:
    """Video copy_message bilan yuborilishi shart (forward EMAS — kanal manbasi ko'rinmasin)."""
    service, _ = _service_with_fake_repo()
    bot = make_bot()
    bot.session.return_value = None
    movie = _movie()

    await service.deliver(bot, movie, user_db_id=99, chat_id=555, lang="uz")

    method = bot.session.call_args.args[1]
    assert isinstance(method, CopyMessage)
    assert method.from_chat_id == movie.channel_id
    assert method.message_id == movie.message_id
    assert method.chat_id == 555


@pytest.mark.asyncio
async def test_deleted_source_deactivates_movie_and_raises() -> None:
    """Manba xabar o'chirilgan (TelegramBadRequest) -> is_active=False + xato."""
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    movie = _movie()
    bot.session.side_effect = TelegramBadRequest(
        method=CopyMessage(
            chat_id=555, from_chat_id=movie.channel_id, message_id=movie.message_id
        ),
        message="message to copy not found",
    )

    with pytest.raises(MovieDeliveryError):
        await service.deliver(bot, movie, user_db_id=99, chat_id=555, lang="uz")

    assert repo.deactivated_ids == [movie.id]
    assert repo.incremented_ids == []  # ko'rish HISOBLANMAYDI — yuborilmadi
    assert repo.views_added == []


@pytest.mark.asyncio
async def test_bot_blocked_deactivates_movie_and_raises() -> None:
    """copy_message uchun kerakli huquq yo'q (TelegramForbiddenError) -> xuddi shu yo'l."""
    service, repo = _service_with_fake_repo()
    bot = make_bot()
    movie = _movie()
    bot.session.side_effect = TelegramForbiddenError(
        method=CopyMessage(
            chat_id=555, from_chat_id=movie.channel_id, message_id=movie.message_id
        ),
        message="bot was kicked from the channel",
    )

    with pytest.raises(MovieDeliveryError):
        await service.deliver(bot, movie, user_db_id=99, chat_id=555, lang="uz")

    assert repo.deactivated_ids == [movie.id]


@pytest.mark.asyncio
async def test_deactivation_failure_notifies_admins() -> None:
    """Xato bo'lganда adminlarga xabar yuboriladi (locale orqali, spec 10.6)."""
    service, _ = _service_with_fake_repo()
    bot = make_bot()
    movie = _movie()

    def _session_side_effect(_bot, method, timeout=None):  # noqa: ARG001
        # copy_message xato beradi; keyingi (admin) send_message'lar o'tadi.
        if isinstance(method, CopyMessage):
            raise TelegramBadRequest(method=method, message="message to copy not found")
        return None

    bot.session.side_effect = _session_side_effect

    with pytest.raises(MovieDeliveryError):
        await service.deliver(bot, movie, user_db_id=99, chat_id=555, lang="uz")

    # bot.session 4 marta chaqirilgan: 1) copy_message (xato berdi),
    # 2-4) har bir admin_id (111,222,333) ga send_message (dead_link_alert).
    sent_texts = [
        call.args[1].text
        for call in bot.session.await_args_list
        if hasattr(call.args[1], "text")
    ]
    assert len(sent_texts) == 3  # uchala admin ham xabar oldi
    assert all("777" in text for text in sent_texts)  # kino kodi xabarda bor
