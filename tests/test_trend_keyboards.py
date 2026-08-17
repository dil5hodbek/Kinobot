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


def test_trend_keyboard_shows_name_and_code() -> None:
    movies = [_FakeMovie(1, "777", "Sarbozlar")]
    markup = trend_keyboard(movies, "uz")

    text = markup.inline_keyboard[0][0].text
    assert "Sarbozlar" in text
    assert "777" in text


def test_trend_keyboard_callback_data_targets_movie() -> None:
    movies = [_FakeMovie(1, "777", "Sarbozlar")]
    markup = trend_keyboard(movies, "uz")

    assert markup.inline_keyboard[0][0].callback_data == "movie:1"


def test_trend_admin_list_keyboard_has_remove_buttons() -> None:
    movies = [_FakeMovie(1, "10", "Kino A"), _FakeMovie(2, "20", "Kino B")]
    markup = trend_admin_list_keyboard(movies)

    datas = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert datas == ["trendrm:1", "trendrm:2"]


def test_trend_pick_keyboard_targets_correct_movies() -> None:
    movies = [_FakeMovie(3, "30", "Kino C")]
    markup = trend_pick_keyboard(movies, "uz")

    btn = markup.inline_keyboard[0][0]
    assert btn.callback_data == "trendpick:3"
    assert "Kino C" in btn.text
    assert "30" in btn.text
