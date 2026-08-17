"""Admin statistika paneli."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.movie_repository import MovieRepository
from app.repositories.user_repository import UserRepository
from app.utils.filters import ButtonText, IsAdmin
from app.utils.format import movie_title
from app.utils.i18n import t

router = Router(name="admin_stats")
router.message.filter(IsAdmin())


@router.message(StateFilter(None), ButtonText("btn_stats"))
async def show_stats(message: Message, lang: str, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    movie_repo = MovieRepository(session)

    total_users = await user_repo.count_total()
    new_today = await user_repo.count_new_today()
    active_7d = await user_repo.count_active_since(7)
    blocked = await user_repo.count_blocked()

    total_movies = await movie_repo.count_total()
    total_views = await movie_repo.sum_views()
    top_movies = await movie_repo.get_top(5)

    if top_movies:
        top_lines = "\n".join(
            f"{i}. {movie_title(m, lang)} — {t('views_label', lang)} {m.views_count}"
            for i, m in enumerate(top_movies, start=1)
        )
    else:
        top_lines = t("stats_no_movies", lang)

    await message.answer(
        t(
            "stats_text",
            lang,
            total_users=total_users,
            new_today=new_today,
            active_7d=active_7d,
            blocked=blocked,
            total_movies=total_movies,
            total_views=total_views,
            top_movies=top_lines,
        )
    )
