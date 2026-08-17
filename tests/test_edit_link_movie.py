"""edit_movie_keyboard va looks_like_url — link-kino tahrirlash imkoniyati.

Avval link-kinolarning `external_url`'ini tahrirlashning umuman iloji yo'q
edi (faqat title/year/genre). Endi link-kino uchun klaviaturada qo'shimcha
"Havola" tugmasi chiqadi, channel-kino uchun esa chiqmaydi.
"""
from __future__ import annotations

from app.keyboards.inline import edit_movie_keyboard
from app.utils.format import looks_like_url


class _FakeMovie:
    def __init__(self, movie_id: int, source_type: str) -> None:
        self.id = movie_id
        self.source_type = source_type


def _callback_datas(markup) -> set[str]:
    return {btn.callback_data for row in markup.inline_keyboard for btn in row}


def test_edit_keyboard_shows_url_button_for_link_movie() -> None:
    movie = _FakeMovie(7, "link")
    markup = edit_movie_keyboard(movie, "uz")
    datas = _callback_datas(markup)
    assert "edit:url:7" in datas
    assert "edit:title:7" in datas


def test_edit_keyboard_hides_url_button_for_channel_movie() -> None:
    movie = _FakeMovie(7, "channel")
    markup = edit_movie_keyboard(movie, "uz")
    datas = _callback_datas(markup)
    assert not any(d.startswith("edit:url:") for d in datas)


def test_looks_like_url_accepts_http_https() -> None:
    assert looks_like_url("https://example.com/movie")
    assert looks_like_url("http://example.com")


def test_looks_like_url_rejects_non_url() -> None:
    assert not looks_like_url("not a url")
    assert not looks_like_url("ftp://example.com")
    assert not looks_like_url("")
