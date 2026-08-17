"""app/handlers/channels.py (foydalanuvchi 'Kanallar' tugmasi) testlari."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.methods import SendMessage

from app.handlers.channels import show_channels
from tests.helpers import make_bot, make_message


class _FakeChannel:
    def __init__(self, username: str) -> None:
        self.username = username
        self.display = f"@{username}"
        self.url = f"https://t.me/{username}"


@pytest.mark.asyncio
async def test_show_channels_marks_subscribed_with_checkmark() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="📢 Kanallar")

    fake_service = AsyncMock()
    fake_service.channels_with_status.return_value = [
        (_FakeChannel("alpha"), True),
        (_FakeChannel("beta"), False),
    ]

    with patch("app.handlers.channels.SubscriptionService", return_value=fake_service):
        await show_channels(message, lang="uz", session=None, redis=None)

    fake_service.channels_with_status.assert_awaited_once_with(bot, 1)
    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    texts = [btn.text for row in method.reply_markup.inline_keyboard for btn in row]
    assert texts[0].startswith("✅")
    assert texts[1].startswith("➕")


@pytest.mark.asyncio
async def test_show_channels_empty_list_shows_empty_message() -> None:
    bot = make_bot()
    bot.session.return_value = None
    message = make_message(bot, 1, text="📢 Kanallar")

    fake_service = AsyncMock()
    fake_service.channels_with_status.return_value = []

    with patch("app.handlers.channels.SubscriptionService", return_value=fake_service):
        await show_channels(message, lang="uz", session=None, redis=None)

    method = bot.session.call_args.args[1]
    assert isinstance(method, SendMessage)
    assert "bo'sh" in method.text
