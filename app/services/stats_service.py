"""Admin statistika biznes logikasi (yig'ish + matn shakllantirish)."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.repositories.movie_repository import MovieRepository
from app.repositories.user_repository import UserRepository
from app.utils.format import movie_title
from app.utils.i18n import t


@dataclass(frozen=True, slots=True)
class BotStats:
    total_users: int
    new_today: int
    active_7d: int
    blocked: int
    total_movies: int
    total_views: int
    top_movies: list[Movie]


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self._user_repo = UserRepository(session)
        self._movie_repo = MovieRepository(session)

    async def collect(self) -> BotStats:
        return BotStats(
            total_users=await self._user_repo.count_total(),
            new_today=await self._user_repo.count_new_today(),
            active_7d=await self._user_repo.count_active_since(7),
            blocked=await self._user_repo.count_blocked(),
            total_movies=await self._movie_repo.count_total(),
            total_views=await self._movie_repo.sum_views(),
            top_movies=await self._movie_repo.get_top(5),
        )

    def format_report(self, stats: BotStats, lang: str) -> str:
        """To'liq statistika matnini yasaydi (top-5 kino qatorlari bilan)."""
        if stats.top_movies:
            top_lines = "\n".join(
                f"{i}. {movie_title(m, lang)} — {t('views_label', lang)} {m.views_count}"
                for i, m in enumerate(stats.top_movies, start=1)
            )
        else:
            top_lines = t("stats_no_movies", lang)

        return t(
            "stats_text",
            lang,
            total_users=stats.total_users,
            new_today=stats.new_today,
            active_7d=stats.active_7d,
            blocked=stats.blocked,
            total_movies=stats.total_movies,
            total_views=stats.total_views,
            top_movies=top_lines,
        )
