"""MovieService.add_link_movie() / add_movie() — repository.create()ga
to'g'ri source_type/maydonlar uzatilishini tekshiradi."""
from __future__ import annotations

import pytest

from app.services.movie_service import MovieService


class _CapturingRepo:
    def __init__(self) -> None:
        self.create_kwargs: dict | None = None

    async def create(self, **kwargs: object) -> object:
        self.create_kwargs = kwargs
        return object()


def _service() -> tuple[MovieService, _CapturingRepo]:
    service = MovieService(session=None)  # type: ignore[arg-type]
    repo = _CapturingRepo()
    service._repo = repo  # type: ignore[attr-defined]
    return service, repo


@pytest.mark.asyncio
async def test_add_link_movie_passes_link_source_type() -> None:
    service, repo = _service()

    await service.add_link_movie(
        code="99",
        external_url="https://x.com/m",
        title_uz="T",
        title_ru=None,
        title_en=None,
        year=2024,
        genre="action",
    )

    assert repo.create_kwargs is not None
    assert repo.create_kwargs["source_type"] == "link"
    assert repo.create_kwargs["external_url"] == "https://x.com/m"
    assert repo.create_kwargs.get("channel_id") is None
    assert repo.create_kwargs.get("message_id") is None


@pytest.mark.asyncio
async def test_add_movie_still_passes_channel_source_type() -> None:
    """Eski (kanal) oqim o'zgarmagan — regressiya tekshiruvi."""
    service, repo = _service()

    await service.add_movie(
        code="1",
        channel_id=100,
        message_id=200,
        title_uz="T",
        title_ru=None,
        title_en=None,
        year=None,
        genre=None,
    )

    assert repo.create_kwargs is not None
    assert repo.create_kwargs["source_type"] == "channel"
    assert repo.create_kwargs["channel_id"] == 100
    assert repo.create_kwargs["message_id"] == 200
    assert repo.create_kwargs.get("external_url") is None
