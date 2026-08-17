"""app/handlers/trend.py — foydalanuvchiga ko'rinadigan trend ro'yxati.

Ro'yxat matn xabarida (nomi + kod), tugmalarda esa faqat kod ko'rinadi —
"kino kodi 7 bo'lsa, '7' tugmasini bossa o'sha kino boradi" talabiga mos.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.methods import SendMessage

from app.handlers.trend import show_trend
from tests.helpers import make_bot, make_message


class _FakeMovie:
    def __init__(self, movie_id: int, code: str, title_uz: str) -> None:
        self.id = movie_id
        self.code = code
        self.title_uz = title_uz
        self.title_ru = None
        self.title_en = None


@pytest.mark.asyncio
async def test_trend_message_lists_name_and_code_buttons_show_only_code() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="🔥 Trend kinolar")

    fake_service = AsyncMock()
    fake_service.get_trending.return_value = [
        _FakeMovie(1, "7", "Sarbozlar"),
        _FakeMovie(2, "12", "Yulduzlar jangi"),
    ]

    with patch("app.handlers.trend.MovieService", return_value=fake_service):
        await show_trend(message, lang="uz", session=None)

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert "Sarbozlar" in method.text
    assert "Kod: 7" in method.text
    assert "Yulduzlar jangi" in method.text
    assert "Kod: 12" in method.text

    button_texts = [btn.text for row in method.reply_markup.inline_keyboard for btn in row]
    assert button_texts == ["🎬 7", "🎬 12"]


@pytest.mark.asyncio
async def test_trend_empty_shows_empty_message() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="🔥 Trend kinolar")

    fake_service = AsyncMock()
    fake_service.get_trending.return_value = []

    with patch("app.handlers.trend.MovieService", return_value=fake_service):
        await show_trend(message, lang="uz", session=None)

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert "yo'q" in method.text
