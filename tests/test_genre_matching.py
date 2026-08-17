"""MovieService.match_genre() / movies_by_genre() testlari.

Foydalanuvchi "romance" deb yozsa — bu funksiyalar mavjud janrlar bilan
ANIQ (fuzzy emas) case-insensitive solishtiradi. Fuzzy bo'lganда tasodifiy
noto'g'ri janr tanlanishi mumkin edi — bu YO'Q yoki ANIQ moslik prinsipi.
"""
from __future__ import annotations

import pytest

from app.services.movie_service import MovieService


class _FakeGenreRepo:
    def __init__(self, genres: list[str], movies_by_genre: dict | None = None) -> None:
        self._genres = genres
        self._movies_by_genre = movies_by_genre or {}
        self.list_genres_calls = 0
        self.get_by_genre_calls: list[tuple[str, int]] = []

    async def list_genres(self) -> list[str]:
        self.list_genres_calls += 1
        return list(self._genres)

    async def get_by_genre(self, genre: str, limit: int = 30) -> list:
        self.get_by_genre_calls.append((genre, limit))
        return self._movies_by_genre.get(genre.lower(), [])


def _service(repo: _FakeGenreRepo) -> MovieService:
    service = MovieService(session=None)  # type: ignore[arg-type]
    service._repo = repo  # type: ignore[attr-defined]
    return service


@pytest.mark.asyncio
async def test_exact_case_insensitive_match() -> None:
    repo = _FakeGenreRepo(["Drama", "Romance", "Comedy"])
    service = _service(repo)

    assert await service.match_genre("romance") == "Romance"
    assert await service.match_genre("DRAMA") == "Drama"
    assert await service.match_genre("  comedy  ") == "Comedy"


@pytest.mark.asyncio
async def test_no_match_returns_none() -> None:
    repo = _FakeGenreRepo(["Drama", "Romance"])
    service = _service(repo)

    assert await service.match_genre("horror") is None


@pytest.mark.asyncio
async def test_partial_text_does_not_match_a_genre() -> None:
    """Fuzzy EMAS — "rom" "Romance"ga mos kelmasligi kerak (aniq moslik)."""
    repo = _FakeGenreRepo(["Romance"])
    service = _service(repo)

    assert await service.match_genre("rom") is None


@pytest.mark.asyncio
async def test_empty_query_returns_none_without_hitting_repo() -> None:
    repo = _FakeGenreRepo(["Drama"])
    service = _service(repo)

    result = await service.match_genre("   ")

    assert result is None
    assert repo.list_genres_calls == 0


@pytest.mark.asyncio
async def test_movies_by_genre_delegates_to_repo() -> None:
    repo = _FakeGenreRepo(["Drama"], movies_by_genre={"drama": ["m1", "m2"]})
    service = _service(repo)

    result = await service.movies_by_genre("drama")

    assert result == ["m1", "m2"]
    assert repo.get_by_genre_calls == [("drama", 30)]
