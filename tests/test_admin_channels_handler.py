"""app/handlers/admin/channels.py — kanallar ro'yxati sarlavhasida son ko'rsatilishi."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.methods import SendMessage

from app.config import settings
from app.handlers.admin.channels import start_add_channel
from tests.helpers import make_bot, make_message


class _FakeChannel:
    def __init__(self, channel_id: int, username: str) -> None:
        self.id = channel_id
        self.channel_username = username


class _FakeState:
    async def set_state(self, _state: object) -> None:
        pass


@pytest.mark.asyncio
async def test_channel_list_title_shows_count() -> None:
    bot = make_bot()
    bot.session.return_value = None
    admin_id = settings.admin_ids[0]
    message = make_message(bot, admin_id, text="btn_add_channel")

    fake_service = AsyncMock()
    fake_service.list_active.return_value = [
        _FakeChannel(1, "alpha"),
        _FakeChannel(2, "beta"),
        _FakeChannel(3, "gamma"),
    ]

    with patch("app.handlers.admin.channels.ChannelService", return_value=fake_service):
        await start_add_channel(message, lang="uz", state=_FakeState(), session=None)

    first_call = bot.session.call_args_list[0]
    method = first_call.args[1]
    assert isinstance(method, SendMessage)
    assert "3" in method.text
