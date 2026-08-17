"""MovieService.add_to_trending/remove_from_trending — qo'lda boshqariladigan
trend ro'yxati biznes logikasi (cheklov, takrorlanish, topilmaslik)."""
from __future__ import annotations

import pytest

from app.config import settings
from app.models.movie import Movie
from app.services.movie_service import AddTrendResult, MovieService


class _FakeTrendRepo:
    def __init__(self, movies: dict[int, Movie]) -> None:
        self._movies = movies
        self.set_trending_calls: list[tuple[int, bool]] = []
        self.lock_calls = 0

    async def get_by_id(self, movie_id: int) -> Movie | None:
        return self._movies.get(movie_id)

    async def count_trending(self) -> int:
        return sum(1 for m in self._movies.values() if m.is_trending)

    async def set_trending(self, movie_id: int, trending: bool) -> None:
        self.set_trending_calls.append((movie_id, trending))
        self._movies[movie_id].is_trending = trending

    async def lock_trending(self) -> None:
        self.lock_calls += 1


def _movie(movie_id: int, *, trending: bool = False) -> Movie:
    return Movie(
        id=movie_id,
        code=str(movie_id),
        title_uz=f"Kino {movie_id}",
        title_ru=None,
        title_en=None,
        year=2024,
        genre="drama",
        views_count=0,
        is_active=True,
        is_trending=trending,
    )


def _service(movies: dict[int, Movie]) -> tuple[MovieService, _FakeTrendRepo]:
    service = MovieService(session=None)  # type: ignore[arg-type]
    repo = _FakeTrendRepo(movies)
    service._repo = repo  # type: ignore[attr-defined]
    return service, repo


@pytest.mark.asyncio
async def test_add_to_trending_success() -> None:
    service, repo = _service({1: _movie(1)})

    result = await service.add_to_trending(1)

    assert result is AddTrendResult.ADDED
    assert repo.set_trending_calls == [(1, True)]
    # Race condition himoyasi: qo'shishdan oldin tranzaksiya qulflanishi kerak.
    assert repo.lock_calls == 1


@pytest.mark.asyncio
async def test_add_to_trending_already_trending() -> None:
    service, repo = _service({1: _movie(1, trending=True)})

    result = await service.add_to_trending(1)

    assert result is AddTrendResult.ALREADY_TRENDING
    assert repo.set_trending_calls == []


@pytest.mark.asyncio
async def test_add_to_trending_not_found() -> None:
    service, repo = _service({})

    result = await service.add_to_trending(999)

    assert result is AddTrendResult.NOT_FOUND
    assert repo.set_trending_calls == []


@pytest.mark.asyncio
async def test_add_to_trending_limit_reached() -> None:
    movies = {
        i: _movie(i, trending=True) for i in range(1, settings.trend_limit + 1)
    }
    movies[999] = _movie(999)  # yangi, hali trend emas
    service, repo = _service(movies)

    result = await service.add_to_trending(999)

    assert result is AddTrendResult.LIMIT_REACHED
    assert repo.set_trending_calls == []


@pytest.mark.asyncio
async def test_remove_from_trending() -> None:
    service, repo = _service({1: _movie(1, trending=True)})

    await service.remove_from_trending(1)

    assert repo.set_trending_calls == [(1, False)]


@pytest.mark.asyncio
async def test_trending_count() -> None:
    service, _ = _service(
        {1: _movie(1, trending=True), 2: _movie(2, trending=False)}
    )

    assert await service.trending_count() == 1
