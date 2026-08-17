"""app/handlers/admin/trend_movies.py — admin trend boshqaruvi oqimi."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.methods import SendMessage

from app.config import settings
from app.handlers.admin.trend_movies import (
    got_trend_query,
    open_trend_movies,
    pick_trend_movie,
    remove_trend_movie,
)
from app.services.movie_service import AddTrendResult
from tests.helpers import make_bot, make_callback, make_message


class _FakeMovie:
    def __init__(self, movie_id: int, code: str, title_uz: str) -> None:
        self.id = movie_id
        self.code = code
        self.title_uz = title_uz
        self.title_ru = None
        self.title_en = None


class _FakeState:
    def __init__(self) -> None:
        self.state: object = None

    async def set_state(self, state: object) -> None:
        self.state = state


def _all_texts(bot) -> list[str]:  # noqa: ANN001
    return [
        c.args[1].text
        for c in bot.session.call_args_list
        if isinstance(c.args[1], SendMessage)
    ]


@pytest.mark.asyncio
async def test_open_trend_movies_shows_list_and_asks_for_more() -> None:
    bot = make_bot()
    bot.session.return_value = None
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text="🔥 Trend kinolar")
    state = _FakeState()

    fake_service = AsyncMock()
    fake_service.get_trending.return_value = [_FakeMovie(1, "10", "Kino A")]

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await open_trend_movies(message, lang="uz", state=state, session=None)

    texts = _all_texts(bot)
    assert any("1/10" in t or "1/" in t for t in texts)


@pytest.mark.asyncio
async def test_add_by_exact_code() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="777")

    fake_service = AsyncMock()
    fake_service.find_by_code_any.return_value = _FakeMovie(5, "777", "Kino")
    fake_service.add_to_trending.return_value = AddTrendResult.ADDED
    fake_service.get_trending.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await got_trend_query(message, lang="uz", session=None)

    fake_service.add_to_trending.assert_awaited_once_with(5)
    texts = _all_texts(bot)
    assert any("qo'shildi" in t for t in texts)


@pytest.mark.asyncio
async def test_add_query_not_found() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="obscure title")

    fake_service = AsyncMock()
    fake_service.find_by_code_any.return_value = None
    fake_service.search.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await got_trend_query(message, lang="uz", session=None)

    fake_service.add_to_trending.assert_not_called()
    texts = _all_texts(bot)
    assert any("topilmadi" in t for t in texts)


@pytest.mark.asyncio
async def test_add_query_multiple_results_shows_picker() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="kino")

    fake_service = AsyncMock()
    fake_service.find_by_code_any.return_value = None
    fake_service.search.return_value = [
        _FakeMovie(1, "1", "Kino A"),
        _FakeMovie(2, "2", "Kino B"),
    ]

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await got_trend_query(message, lang="uz", session=None)

    fake_service.add_to_trending.assert_not_called()
    method = bot.session.call_args.args[1]
    datas = {btn.callback_data for row in method.reply_markup.inline_keyboard for btn in row}
    assert datas == {"trendpick:1", "trendpick:2"}


@pytest.mark.asyncio
async def test_add_already_trending_message() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="777")

    fake_service = AsyncMock()
    fake_service.find_by_code_any.return_value = _FakeMovie(5, "777", "Kino")
    fake_service.add_to_trending.return_value = AddTrendResult.ALREADY_TRENDING
    fake_service.get_trending.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await got_trend_query(message, lang="uz", session=None)

    texts = _all_texts(bot)
    assert any("allaqachon" in t for t in texts)


@pytest.mark.asyncio
async def test_add_limit_reached_message() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="777")

    fake_service = AsyncMock()
    fake_service.find_by_code_any.return_value = _FakeMovie(5, "777", "Kino")
    fake_service.add_to_trending.return_value = AddTrendResult.LIMIT_REACHED
    fake_service.get_trending.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await got_trend_query(message, lang="uz", session=None)

    texts = _all_texts(bot)
    assert any("to'liq" in t for t in texts)


@pytest.mark.asyncio
async def test_pick_trend_movie_callback_adds() -> None:
    bot = make_bot()
    bot.session.return_value = None
    callback = make_callback(bot, 1, data="trendpick:7", chat_id=1)

    fake_service = AsyncMock()
    fake_service.add_to_trending.return_value = AddTrendResult.ADDED
    fake_service.get_trending.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await pick_trend_movie(callback, lang="uz", session=None)

    fake_service.add_to_trending.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_remove_trend_movie_callback() -> None:
    bot = make_bot()
    bot.session.return_value = None
    callback = make_callback(bot, 1, data="trendrm:7", chat_id=1)

    fake_service = AsyncMock()
    fake_service.get_trending.return_value = []

    with patch(
        "app.handlers.admin.trend_movies.MovieService", return_value=fake_service
    ):
        await remove_trend_movie(callback, lang="uz", session=None)

    fake_service.remove_from_trending.assert_awaited_once_with(7)
    texts = _all_texts(bot)
    assert any("olib tashlandi" in t for t in texts)
