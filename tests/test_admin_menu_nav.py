"""Admin 2 qavatli menyu navigatsiyasi — hub/submenu almashtirish.

Mavjud amal-tugmalar (btn_add_movie va h.k.) o'zgarmagan — bu testlar
faqat YANGI navigatsiya (hub -> submenu -> orqaga -> oddiy menyu)
to'g'ri reply-klaviaturani ko'rsatishini tasdiqlaydi.
"""
from __future__ import annotations

import pytest
from aiogram.methods import SendMessage
from aiogram.types import ReplyKeyboardMarkup

from app.handlers.admin.panel import (
    back_to_hub,
    open_management_menu,
    open_movies_menu,
    open_user_menu,
)
from tests.helpers import make_bot, make_message


def _button_texts(markup: ReplyKeyboardMarkup) -> set[str]:
    return {btn.text for row in markup.keyboard for btn in row}


@pytest.mark.asyncio
async def test_open_movies_menu_shows_movie_buttons() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1)

    await open_movies_menu(message, lang="uz")

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    texts = _button_texts(method.reply_markup)
    assert "➕ Kino qo'shish" in texts
    assert "🔗 Link qo'shish" in texts
    assert "🔙 Orqaga" in texts


@pytest.mark.asyncio
async def test_open_management_menu_shows_management_buttons() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1)

    await open_management_menu(message, lang="uz")

    method = bot.session.call_args.args[1]
    texts = _button_texts(method.reply_markup)
    assert "📊 Statistika" in texts
    assert "📣 Xabar yuborish" in texts
    assert "🔙 Orqaga" in texts


@pytest.mark.asyncio
async def test_back_to_hub_shows_hub_buttons() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1)

    await back_to_hub(message, lang="uz")

    method = bot.session.call_args.args[1]
    texts = _button_texts(method.reply_markup)
    assert "🎬 Kinolar" in texts
    assert "📊 Boshqaruv" in texts


@pytest.mark.asyncio
async def test_user_menu_shows_regular_user_buttons() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1)

    await open_user_menu(message, lang="uz")

    method = bot.session.call_args.args[1]
    texts = _button_texts(method.reply_markup)
    assert "🔍 Qidiruv" in texts
    assert "🔥 Trend kinolar" in texts
