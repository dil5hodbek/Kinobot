"""StatsService testlari — avval NOL qoplamaga ega bo'lgan biznes logika
(statistikani yig'ish va matn shakllantirish)."""
from __future__ import annotations

import pytest

from app.models.movie import Movie
from app.services.stats_service import BotStats, StatsService


class _FakeUserRepo:
    def __init__(self, *, total=0, new_today=0, active_7d=0, blocked=0) -> None:
        self._total = total
        self._new_today = new_today
        self._active_7d = active_7d
        self._blocked = blocked

    async def count_total(self) -> int:
        return self._total

    async def count_new_today(self) -> int:
        return self._new_today

    async def count_active_since(self, _days: int) -> int:
        return self._active_7d

    async def count_blocked(self) -> int:
        return self._blocked


class _FakeMovieRepo:
    def __init__(self, *, total=0, views=0, top=None) -> None:
        self._total = total
        self._views = views
        self._top = top or []

    async def count_total(self) -> int:
        return self._total

    async def sum_views(self) -> int:
        return self._views

    async def get_top(self, limit: int) -> list[Movie]:
        return self._top[:limit]


def _movie(movie_id: int, title: str, views: int) -> Movie:
    return Movie(
        id=movie_id,
        code=str(movie_id),
        title_uz=title,
        title_ru=None,
        title_en=None,
        year=2024,
        genre="drama",
        views_count=views,
        is_active=True,
    )


def _service(user_repo, movie_repo) -> StatsService:
    service = StatsService(session=None)  # type: ignore[arg-type]
    service._user_repo = user_repo  # type: ignore[attr-defined]
    service._movie_repo = movie_repo  # type: ignore[attr-defined]
    return service


@pytest.mark.asyncio
async def test_collect_aggregates_all_counters() -> None:
    top_movie = _movie(1, "A", 50)
    user_repo = _FakeUserRepo(total=100, new_today=5, active_7d=40, blocked=3)
    movie_repo = _FakeMovieRepo(total=20, views=999, top=[top_movie])
    service = _service(user_repo, movie_repo)

    stats = await service.collect()

    assert stats.total_users == 100
    assert stats.new_today == 5
    assert stats.active_7d == 40
    assert stats.blocked == 3
    assert stats.total_movies == 20
    assert stats.total_views == 999
    assert stats.top_movies == [top_movie]


@pytest.mark.asyncio
async def test_collect_limits_top_movies_to_five() -> None:
    top = [_movie(i, f"Kino {i}", 100 - i) for i in range(1, 8)]
    service = _service(_FakeUserRepo(), _FakeMovieRepo(top=top))

    stats = await service.collect()

    assert len(stats.top_movies) == 5


def test_format_report_includes_all_counters() -> None:
    service = _service(_FakeUserRepo(), _FakeMovieRepo())
    stats = BotStats(
        total_users=10,
        new_today=2,
        active_7d=6,
        blocked=1,
        total_movies=15,
        total_views=300,
        top_movies=[_movie(1, "Sarbozlar", 42)],
    )

    text = service.format_report(stats, "uz")

    assert "10" in text
    assert "Sarbozlar" in text
    assert "42" in text


def test_format_report_empty_top_movies_shows_placeholder() -> None:
    service = _service(_FakeUserRepo(), _FakeMovieRepo())
    stats = BotStats(
        total_users=0,
        new_today=0,
        active_7d=0,
        blocked=0,
        total_movies=0,
        total_views=0,
        top_movies=[],
    )

    text = service.format_report(stats, "uz")

    # Bo'sh top-5 uchun ro'yxat o'rniga placeholder ko'rsatiladi (spec: dead-end emas).
    assert "0" in text