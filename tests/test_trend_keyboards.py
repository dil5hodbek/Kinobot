"""trend_keyboard (foydalanuvchi) va trend_admin_list_keyboard/trend_pick_keyboard
(admin) testlari."""
from __future__ import annotations

from app.keyboards.inline import (
    trend_admin_list_keyboard,
    trend_keyboard,
    trend_pick_keyboard,
)


class _FakeMovie:
    def __init__(self, movie_id: int, code: str, title_uz: str) -> None:
        self.id = movie_id
        self.code = code
        self.title_uz = title_uz
        self.title_ru = None
        self.title_en = None


def test_trend_keyboard_button_shows_code_only() -> None:
    """Tugmada faqat kod ko'rinadi (tez tanlash uchun) — nom alohida matn xabarida."""
    movies = [_FakeMovie(1, "777", "Sarbozlar")]
    markup = trend_keyboard(movies)

    text = markup.inline_keyboard[0][0].text
    assert "777" in text
    assert "Sarbozlar" not in text


def test_trend_keyboard_callback_data_targets_movie() -> None:
    movies = [_FakeMovie(1, "777", "Sarbozlar")]
    markup = trend_keyboard(movies)

    assert markup.inline_keyboard[0][0].callback_data == "movie:1"


def test_trend_keyboard_wraps_into_rows_of_five() -> None:
    movies = [_FakeMovie(i, str(i), f"Kino {i}") for i in range(1, 8)]
    markup = trend_keyboard(movies)

    assert len(markup.inline_keyboard[0]) == 5
    assert len(markup.inline_keyboard[1]) == 2


def test_trend_admin_list_keyboard_has_remove_buttons() -> None:
    movies = [_FakeMovie(1, "10", "Kino A"), _FakeMovie(2, "20", "Kino B")]
    markup = trend_admin_list_keyboard(movies, "uz")

    datas = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert datas == ["trendrm:1", "trendrm:2"]


def test_trend_admin_list_keyboard_uses_language_specific_title() -> None:
    movie = _FakeMovie(1, "10", "Kino A")
    movie.title_ru = "Кино А"
    markup = trend_admin_list_keyboard([movie], "ru")

    assert "Кино А" in markup.inline_keyboard[0][0].text


def test_trend_pick_keyboard_targets_correct_movies() -> None:
    movies = [_FakeMovie(3, "30", "Kino C")]
    markup = trend_pick_keyboard(movies, "uz")

    btn = markup.inline_keyboard[0][0]
    assert btn.callback_data == "trendpick:3"
    assert "Kino C" in btn.text
    assert "30" in btn.text
