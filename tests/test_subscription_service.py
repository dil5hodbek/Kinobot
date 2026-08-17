"""SubscriptionService testlari — majburiy obuna tekshiruvi + Redis kesh.

Bu butun foydalanuvchi oqimini boshqaradi (spec 5.2): agar mantiq teskari
bo'lsa (masalan obuna bo'lganlarni ham to'sib qo'ysa, yoki aksincha hech
kimni to'smasa), bot butunlay ishlamay qoladi yoki majburiy obuna talabi
soxta bo'lib qoladi.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import GetChatMember
from aiogram.types import ChatMemberLeft, ChatMemberMember

from app.services.subscription_service import SubscriptionService
from tests.helpers import make_bot


class _EmptyScalars:
    def all(self) -> list:
        return []


class _EmptyResult:
    def scalars(self) -> _EmptyScalars:
        return _EmptyScalars()


class _FakeSession:
    """AsyncSession o'rniga — ChannelRepository.get_active() bo'sh ro'yxat qaytaradi.

    Shunda `_all_channels()` faqat .env dagi REQUIRED_CHANNELS'ni ishlatadi
    (conftest: "@alpha, beta , gamma" -> ["alpha", "beta", "gamma"]) —
    natija DB holatidan qat'i nazar oldindan aytib bo'ladigan bo'ladi.
    """

    async def execute(self, _stmt: object) -> _EmptyResult:
        return _EmptyResult()


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value


def _mock_member_status(bot, status: ChatMemberStatus) -> None:  # noqa: ANN001
    """bot.get_chat_member(...) chaqirilsa shu holatdagi a'zolikni qaytaradi."""
    cls = ChatMemberMember if status == ChatMemberStatus.MEMBER else ChatMemberLeft
    bot.session.return_value = cls.model_construct(status=status, user=None)


@pytest.mark.asyncio
async def test_member_status_is_subscribed() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.MEMBER)
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service._is_subscribed(bot, "alpha", user_id=1) is True


@pytest.mark.asyncio
async def test_administrator_status_is_subscribed() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.ADMINISTRATOR)
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service._is_subscribed(bot, "alpha", user_id=1) is True


@pytest.mark.asyncio
async def test_left_status_is_not_subscribed() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.LEFT)
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service._is_subscribed(bot, "alpha", user_id=1) is False


@pytest.mark.asyncio
async def test_kicked_status_is_not_subscribed() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.KICKED)
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service._is_subscribed(bot, "alpha", user_id=1) is False


@pytest.mark.asyncio
async def test_result_is_cached_after_first_check() -> None:
    """Ikkinchi tekshiruv Redis keshdan olinadi — Telegram API qayta chaqirilmaydi."""
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.MEMBER)
    redis = _FakeRedis()
    service = SubscriptionService(_FakeSession(), redis)

    first = await service._is_subscribed(bot, "alpha", user_id=1)
    bot.session.reset_mock()

    second = await service._is_subscribed(bot, "alpha", user_id=1)

    assert first is True
    assert second is True
    bot.session.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_error_fails_open() -> None:
    """Kanal topilmasa / bot admin bo'lmasa — foydalanuvchini BLOKLAMAYMIZ."""
    bot = make_bot()
    bot.session = AsyncMock(
        side_effect=TelegramAPIError(
            method=GetChatMember(chat_id="@alpha", user_id=1),
            message="kanal topilmadi",
        )
    )
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service._is_subscribed(bot, "alpha", user_id=1) is True


@pytest.mark.asyncio
async def test_get_unsubscribed_checks_every_env_channel() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.LEFT)  # hech qaysi kanalga obuna emas
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    unsubscribed = await service.get_unsubscribed(bot, user_id=1)

    assert {c.username for c in unsubscribed} == {"alpha", "beta", "gamma"}


@pytest.mark.asyncio
async def test_is_fully_subscribed_true_when_all_channels_ok() -> None:
    bot = make_bot()
    _mock_member_status(bot, ChatMemberStatus.MEMBER)
    service = SubscriptionService(_FakeSession(), _FakeRedis())

    assert await service.is_fully_subscribed(bot, user_id=1) is True
