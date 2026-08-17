"""channel_intake.intake_new_post() — race-condition tuzatishi testi.

Bir nechta kanal posti deyarli bir vaqtda kelsa (masalan bot qayta ulangach
navbatdagi postlar bittada keladi), ikkalasi ham code_exists() tekshiruvini
"band emas" deb o'tishi mumkin. Bu test aynan shu holatni simulyatsiya
qiladi: tekshiruv "bo'sh" deydi, keyin haqiqiy INSERT (flush) unique
constraint bilan IntegrityError beradi — handler buni ushlab, sessiyani
rollback qilib, adminlarga to'qnashuv haqida xabar berishi va KRASH
BO'LMASLIGI kerak.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.handlers.channel_intake import intake_new_post
from app.models.movie import Movie
from aiogram.types import Chat, Message
from tests.helpers import make_bot, make_user


class _NoneResult:
    def scalar_one_or_none(self) -> None:
        return None


class _RacingSession:
    """code_exists() -> bo'sh (False), create()ning flush()i esa IntegrityError."""

    def __init__(self) -> None:
        self.rolled_back = False
        self.added: list[Movie] = []

    async def execute(self, _stmt: object) -> _NoneResult:
        return _NoneResult()

    def add(self, obj: Movie) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        raise IntegrityError("INSERT", {}, Exception("unique_violation: movies_code_key"))

    async def rollback(self) -> None:
        self.rolled_back = True


def _channel_post(bot, caption: str) -> Message:  # noqa: ANN001
    return Message.model_construct(
        message_id=10,
        date=datetime.now(timezone.utc),
        chat=Chat(id=settings.storage_channel_id, type="channel"),
        from_user=make_user(1),  # _has_media/_is_storage'da ishlatilmaydi
        caption=caption,
        video=object(),  # _has_media uchun — faqat truthy bo'lishi kerak
    ).as_(bot)


@pytest.mark.asyncio
async def test_code_collision_race_does_not_crash_and_rolls_back() -> None:
    bot = make_bot()
    bot.session.return_value = None  # _notify_admins muvaffaqiyatli o'tadi
    session = _RacingSession()
    message = _channel_post(bot, "#777\nNom: Poyga")

    # Krash bo'lmasligi (IntegrityError handler ichida ushlanishi) — asosiy tekshiruv.
    await intake_new_post(message, session)  # type: ignore[arg-type]

    assert session.rolled_back is True
    assert len(session.added) == 1  # urinish bo'lgan, lekin commit qilinmagan


@pytest.mark.asyncio
async def test_code_collision_race_notifies_admins() -> None:
    bot = make_bot()
    bot.session.return_value = None
    session = _RacingSession()
    message = _channel_post(bot, "#777\nNom: Poyga")

    await intake_new_post(message, session)  # type: ignore[arg-type]

    sent_texts = [
        call.args[1].text
        for call in bot.session.await_args_list
        if hasattr(call.args[1], "text")
    ]
    assert len(sent_texts) == len(settings.admin_ids)
    assert all("777" in text for text in sent_texts)
