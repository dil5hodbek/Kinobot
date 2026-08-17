"""Config parsing testlari."""
from __future__ import annotations

from app.config import settings


def test_admin_ids_parsed_to_int_list() -> None:
    assert settings.admin_ids == [111, 222, 333]
    assert all(isinstance(x, int) for x in settings.admin_ids)


def test_required_channels_stripped_and_no_at() -> None:
    assert settings.required_channels == ["alpha", "beta", "gamma"]


def test_database_url_is_asyncpg() -> None:
    url = settings.database_url
    assert url.startswith("postgresql+asyncpg://")
    assert "@" in url and "/" in url


def test_redis_url_format() -> None:
    assert settings.redis_url.startswith("redis://")
