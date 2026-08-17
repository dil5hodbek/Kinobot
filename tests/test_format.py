"""movie_title fallback logikasi testlari."""
from __future__ import annotations

from app.models.movie import Movie
from app.utils.format import movie_title


def _movie(**kw: object) -> Movie:
    m = Movie(
        code="1",
        channel_id=-100,
        message_id=1,
        title_uz="Uz nomi",
        title_ru=kw.get("title_ru"),
        title_en=kw.get("title_en"),
    )
    return m


def test_title_returns_requested_language() -> None:
    m = _movie(title_ru="Ру название", title_en="En title")
    assert movie_title(m, "ru") == "Ру название"
    assert movie_title(m, "en") == "En title"
    assert movie_title(m, "uz") == "Uz nomi"


def test_title_falls_back_to_uz_when_missing() -> None:
    m = _movie(title_ru=None, title_en=None)
    assert movie_title(m, "ru") == "Uz nomi"
    assert movie_title(m, "en") == "Uz nomi"


def test_title_unknown_lang_falls_back() -> None:
    m = _movie()
    assert movie_title(m, "xx") == "Uz nomi"
