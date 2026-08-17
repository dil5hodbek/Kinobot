"""IsAdmin filter testlari — admin panelga kirish nazorati.

Regressiya bo'lsa (masalan admin_ids noto'g'ri parse qilinsa, yoki filter
noto'g'ri handlerга ulansa) — admin panel (broadcast, statistika, kino
o'chirish) istalgan foydalanuvchiga ochiladi. Shuning uchun bu eng arzon,
lekin eng muhim testlardan biri.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.utils.filters import IsAdmin
from tests.helpers import make_bot, make_callback, make_message


@pytest.mark.asyncio
async def test_admin_id_allowed_for_message() -> None:
    admin_id = settings.admin_ids[0]
    bot = make_bot()
    message = make_message(bot, admin_id)

    assert await IsAdmin()(message) is True


@pytest.mark.asyncio
async def test_non_admin_id_rejected_for_message() -> None:
    bot = make_bot()
    message = make_message(bot, 999_999_999)  # admin_ids (conftest: 111,222,333) da yo'q

    assert await IsAdmin()(message) is False


@pytest.mark.asyncio
async def test_admin_id_allowed_for_callback_query() -> None:
    admin_id = settings.admin_ids[-1]
    bot = make_bot()
    callback = make_callback(bot, admin_id)

    assert await IsAdmin()(callback) is True


@pytest.mark.asyncio
async def test_non_admin_id_rejected_for_callback_query() -> None:
    bot = make_bot()
    callback = make_callback(bot, 999_999_999)

    assert await IsAdmin()(callback) is False


def test_every_configured_admin_id_is_recognized() -> None:
    """conftest'даgi barcha admin_id'lar (111,222,333) ro'yxatga to'g'ri parse bo'lgan."""
    assert settings.admin_ids == [111, 222, 333]
