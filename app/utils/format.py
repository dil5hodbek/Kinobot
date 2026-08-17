"""Kichik formatlash yordamchilari."""
from __future__ import annotations

from app.models.movie import Movie


def movie_title(movie: Movie, lang: str) -> str:
    """Foydalanuvchi tiliga mos kino nomi (bo'sh bo'lsa o'zbekchaga qaytadi)."""
    mapping = {
        "uz": movie.title_uz,
        "ru": movie.title_ru,
        "en": movie.title_en,
    }
    return mapping.get(lang) or movie.title_uz
