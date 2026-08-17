"""UserService.get_or_create() — race-condition tuzatishi testlari.

Ikkita update deyarli bir vaqtda kelsa (masalan /start ikki marta), ikkalasi
ham "user yo'q" deb yaratishga urinishi mumkin. Bu testlar shu holatni
simulyatsiya qiladi: birinchi get_by_telegram_id() None qaytaradi, create()
IntegrityError beradi (boshqa update allaqachon commit qilgan), va service
buni ushlab, allaqachon yaratilgan qatorni to'g'ri qaytarishi kerak —
butun update yiqilib, javob yuborilmay qolmasligi kerak.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.services.user_service import UserService


class _FakeSession:
    """AsyncSession.begin_nested() o'rniga — no-op SAVEPOINT (xato tashqariga chiqadi)."""

    @asynccontextmanager
    async def begin_nested(self):
        yield


class _RacingRepo:
    """Birinchi get_by_telegram_id -> None, create -> IntegrityError,
    ikkinchi get_by_telegram_id -> "raqib" allaqachon yaratgan qator."""

    def __init__(self, winner: User) -> None:
        self._winner = winner
        self._get_calls = 0
        self.create_calls = 0
        self.touched_ids: list[int] = []

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        self._get_calls += 1
        return None if self._get_calls == 1 else self._winner

    async def create(self, **kwargs: object) -> User:
        self.create_calls += 1
        raise IntegrityError("INSERT", {}, Exception("unique_violation"))

    async def touch_last_active(self, user_id: int) -> None:
        self.touched_ids.append(user_id)


class _NormalRepo:
    """Race yo'q — oddiy yaratish."""

    def __init__(self) -> None:
        self.created: User | None = None
        self.touched_ids: list[int] = []

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return None

    async def create(self, **kwargs: object) -> User:
        self.created = User(id=1, **kwargs)
        return self.created

    async def touch_last_active(self, user_id: int) -> None:
        self.touched_ids.append(user_id)


class _ExistingRepo:
    """Foydalanuvchi allaqachon bor — create() umuman chaqirilmasligi kerak."""

    def __init__(self, existing: User) -> None:
        self._existing = existing
        self.touched_ids: list[int] = []
        self.create_called = False

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return self._existing

    async def create(self, **kwargs: object) -> User:
        self.create_called = True
        raise AssertionError("create() chaqirilmasligi kerak edi")

    async def touch_last_active(self, user_id: int) -> None:
        self.touched_ids.append(user_id)


@pytest.mark.asyncio
async def test_concurrent_insert_recovers_via_existing_row() -> None:
    winner = User(
        id=42, telegram_id=555, username="race", full_name="Race", language="uz"
    )
    service = UserService(_FakeSession())  # type: ignore[arg-type]
    repo = _RacingRepo(winner)
    service._repo = repo  # type: ignore[attr-defined]

    user, is_new = await service.get_or_create(555, "race", "Race")

    assert user is winner
    assert is_new is False
    assert repo.create_calls == 1  # bir marta urinди, ushlandi, qayta urinmadi
    assert repo.touched_ids == [42]  # g'olib qatorga last_active yangilandi


@pytest.mark.asyncio
async def test_no_race_creates_normally() -> None:
    service = UserService(_FakeSession())  # type: ignore[arg-type]
    repo = _NormalRepo()
    service._repo = repo  # type: ignore[attr-defined]

    user, is_new = await service.get_or_create(777, "new", "New")

    assert is_new is True
    assert user is repo.created
    assert repo.touched_ids == []  # yangi userда touch shart emas


@pytest.mark.asyncio
async def test_existing_user_skips_create_entirely() -> None:
    existing = User(
        id=1, telegram_id=999, username="old", full_name="Old", language="uz"
    )
    service = UserService(_FakeSession())  # type: ignore[arg-type]
    repo = _ExistingRepo(existing)
    service._repo = repo  # type: ignore[attr-defined]

    user, is_new = await service.get_or_create(999, "old", "Old")

    assert user is existing
    assert is_new is False
    assert repo.create_called is False
    assert repo.touched_ids == [1]
