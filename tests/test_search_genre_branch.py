"""search.py — janr filiali: kod tekshiruvidan keyin, fuzzy nom
qidiruvidan OLDIN tekshiriladi. Janr topilsa ro'yxat, topilmasa oddiy
fuzzy qidiruvga tushadi (dead-end emas)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.methods import SendMessage

from app.handlers.search import handle_text_search
from app.models.user import User
from tests.helpers import make_bot, make_message


def _user(uid: int = 1) -> User:
    return User(id=uid, telegram_id=uid, username=None, full_name=None, language="uz")


class _FakeMovie:
    def __init__(self, movie_id: int, code: str, title_uz: str) -> None:
        self.id = movie_id
        self.code = code
        self.title_uz = title_uz
        self.title_ru = None
        self.title_en = None


@pytest.mark.asyncio
async def test_genre_query_shows_genre_list_not_fuzzy_search() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="romance")

    fake_service = AsyncMock()
    fake_service.find_by_code.return_value = None
    fake_service.match_genre.return_value = "Romance"
    fake_service.movies_by_genre.return_value = [_FakeMovie(1, "10", "Sevgi")]

    with patch("app.handlers.search.MovieService", return_value=fake_service):
        await handle_text_search(message, user=_user(), lang="uz", session=None)

    fake_service.match_genre.assert_awaited_once_with("romance")
    fake_service.search.assert_not_called()  # fuzzy qidiruv chaqirilmadi
    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert "Romance" in method.text


@pytest.mark.asyncio
async def test_no_genre_match_falls_back_to_fuzzy_search() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="some title")

    fake_service = AsyncMock()
    fake_service.find_by_code.return_value = None
    fake_service.match_genre.return_value = None
    fake_service.search.return_value = []

    with patch("app.handlers.search.MovieService", return_value=fake_service):
        await handle_text_search(message, user=_user(), lang="uz", session=None)

    fake_service.search.assert_awaited_once_with("some title")


@pytest.mark.asyncio
async def test_genre_match_but_no_active_movies_falls_back_to_fuzzy() -> None:
    """Himoya: genre ro'yxatda bor-у, faol kino yo'q bo'lsa — o'lik oxir emas."""
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="obscure")

    fake_service = AsyncMock()
    fake_service.find_by_code.return_value = None
    fake_service.match_genre.return_value = "Obscure"
    fake_service.movies_by_genre.return_value = []
    fake_service.search.return_value = []

    with patch("app.handlers.search.MovieService", return_value=fake_service):
        await handle_text_search(message, user=_user(), lang="uz", session=None)

    fake_service.search.assert_awaited_once_with("obscure")


@pytest.mark.asyncio
async def test_numeric_code_query_never_checks_genre() -> None:
    """Raqamli kod yo'li janr tekshiruvidan OLDIN va mustaqil ishlaydi."""
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="777")

    fake_service = AsyncMock()
    fake_service.find_by_code.return_value = None

    with patch("app.handlers.search.MovieService", return_value=fake_service):
        await handle_text_search(message, user=_user(), lang="uz", session=None)

    fake_service.match_genre.assert_not_called()


@pytest.mark.asyncio
async def test_alphanumeric_code_query_is_delivered_directly() -> None:
    """Admin "top-uz" kabi alifbo-raqamli kod bilan kino qo'shishi mumkin —
    foydalanuvchi aynan shu kodni yozganda genre/fuzzy'ga tushmasdan
    darhol topilishi kerak (avval faqat sof raqam kod deb hisoblanardi)."""
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="top-uz")

    movie = _FakeMovie(5, "top-uz", "Yulduzlar jangi")
    fake_service = AsyncMock()
    fake_service.find_by_code.return_value = movie

    with patch("app.handlers.search.MovieService", return_value=fake_service):
        await handle_text_search(message, user=_user(), lang="uz", session=None)

    fake_service.find_by_code.assert_awaited_once_with("top-uz")
    fake_service.deliver.assert_awaited_once()
    fake_service.match_genre.assert_not_called()
    fake_service.search.assert_not_called()
