"""MovieService.resolve_admin_query() — o'chirish va trendga qo'shish oqimlari
uchun umumiy qidiruv (kod/nom). Avval bu mantiq har ikkala faylda mustaqil
yozilgan edi va trend_movies.py "sof raqam bo'lsa fuzzy'ga tushmaslik"
himoyasini yo'qotib qo'ygan edi — shu regressiyani ushlab turish uchun."""
from __future__ import annotations

import pytest

from app.models.movie import Movie
from app.services.movie_service import MovieService


class _FakeRepo:
    def __init__(self, by_code: dict[str, Movie] | None = None) -> None:
        self._by_code = by_code or {}

    async def get_by_code_any(self, code: str) -> Movie | None:
        return self._by_code.get(code)


def _movie(movie_id: int, code: str, title: str) -> Movie:
    return Movie(
        id=movie_id,
        code=code,
        title_uz=title,
        title_ru=None,
        title_en=None,
        year=2024,
        genre="drama",
        views_count=0,
        is_active=True,
    )


def _service(repo: _FakeRepo, search_results: list[Movie]) -> MovieService:
    service = MovieService(session=None)  # type: ignore[arg-type]
    service._repo = repo  # type: ignore[attr-defined]

    async def _fake_search(_query: str) -> list[Movie]:
        return search_results

    service.search = _fake_search  # type: ignore[method-assign]
    return service


@pytest.mark.asyncio
async def test_exact_code_match_wins() -> None:
    movie = _movie(1, "777", "Kino")
    service = _service(_FakeRepo({"777": movie}), search_results=[])

    lookup = await service.resolve_admin_query("777")

    assert lookup.movie is movie
    assert lookup.candidates == []


@pytest.mark.asyncio
async def test_alphanumeric_code_match_wins() -> None:
    """Kod sof raqam bo'lishi shart emas — admin har qanday kod bilan qo'shishi mumkin."""
    movie = _movie(1, "top-uz", "Kino")
    service = _service(_FakeRepo({"top-uz": movie}), search_results=[])

    lookup = await service.resolve_admin_query("top-uz")

    assert lookup.movie is movie


@pytest.mark.asyncio
async def test_numeric_miss_does_not_fall_through_to_fuzzy_search() -> None:
    """Reg-test: trend_movies.py bu himoyani yo'qotgan edi — sof raqamli kod
    topilmasa, fuzzy nom qidiruviga UMUMAN tushmasligi kerak."""
    unrelated = _movie(99, "5", "42-chi mavzu")
    service = _service(_FakeRepo({}), search_results=[unrelated])

    lookup = await service.resolve_admin_query("42")

    assert lookup.movie is None
    assert lookup.candidates == []


@pytest.mark.asyncio
async def test_non_numeric_miss_falls_through_to_fuzzy_single_result() -> None:
    movie = _movie(1, "9", "Yulduzlar jangi")
    service = _service(_FakeRepo({}), search_results=[movie])

    lookup = await service.resolve_admin_query("yulduzlar")

    assert lookup.movie is movie
    assert lookup.candidates == []


@pytest.mark.asyncio
async def test_fuzzy_multiple_results_returned_as_candidates() -> None:
    a = _movie(1, "1", "Kino A")
    b = _movie(2, "2", "Kino B")
    service = _service(_FakeRepo({}), search_results=[a, b])

    lookup = await service.resolve_admin_query("kino")

    assert lookup.movie is None
    assert lookup.candidates == [a, b]


@pytest.mark.asyncio
async def test_fuzzy_no_results() -> None:
    service = _service(_FakeRepo({}), search_results=[])

    lookup = await service.resolve_admin_query("obscure title")

    assert lookup.movie is None
    assert lookup.candidates == []
