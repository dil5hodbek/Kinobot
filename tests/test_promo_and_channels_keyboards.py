"""Reklama tugmalari (promo_keyboard/movie_link_keyboard) va
kanallar ro'yxatidagi obuna belgisi (channels_list_keyboard) testlari."""
from __future__ import annotations

from app.config import settings
from app.keyboards.inline import channels_list_keyboard, movie_link_keyboard, promo_keyboard


class _FakeChannel:
    def __init__(self, username: str) -> None:
        self.username = username
        self.display = f"@{username}"
        self.url = f"https://t.me/{username}"


def _urls(markup) -> list[str]:
    return [btn.url for row in markup.inline_keyboard for btn in row if btn.url]


def test_promo_keyboard_links_to_bot_and_channel() -> None:
    markup = promo_keyboard("uz")
    urls = _urls(markup)

    assert f"https://t.me/{settings.promo_bot_username}" in urls
    assert f"https://t.me/{settings.promo_channel_username}" in urls
    assert len(urls) == 2


def test_movie_link_keyboard_includes_watch_link_plus_promo() -> None:
    markup = movie_link_keyboard("https://example.com/movie.mp4", "uz")
    urls = _urls(markup)

    assert "https://example.com/movie.mp4" in urls
    assert f"https://t.me/{settings.promo_bot_username}" in urls
    assert f"https://t.me/{settings.promo_channel_username}" in urls
    assert len(urls) == 3


def test_channels_list_keyboard_marks_subscribed_with_checkmark() -> None:
    channels_status = [
        (_FakeChannel("alpha"), True),
        (_FakeChannel("beta"), False),
    ]

    markup = channels_list_keyboard(channels_status)
    texts = [btn.text for row in markup.inline_keyboard for btn in row]

    assert texts[0].startswith("✅")
    assert texts[1].startswith("➕")


def test_channels_list_keyboard_urls_unchanged() -> None:
    channels_status = [(_FakeChannel("alpha"), True)]
    markup = channels_list_keyboard(channels_status)

    assert _urls(markup) == ["https://t.me/alpha"]
