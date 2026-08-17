"""Kanal caption parser (movie_caption) testlari."""
from __future__ import annotations

from app.utils.movie_caption import parse_movie_caption


def test_basic_format() -> None:
    p = parse_movie_caption("#1\nNom: Robotar\nJanr: drama")
    assert p.code == "1"
    assert p.title == "Robotar"
    assert p.genre == "drama"
    assert p.is_complete
    assert p.has_markers


def test_with_year_and_order_independent() -> None:
    p = parse_movie_caption("Janr: komediya\nYil: 2024\n#777\nNomi: Kulgi")
    assert p.code == "777"
    assert p.title == "Kulgi"
    assert p.genre == "komediya"
    assert p.year == 2024


def test_hash_with_trailing_annotation() -> None:
    # "#1 - kino kodi" kabi izohli satr ham ishlashi kerak
    p = parse_movie_caption("#1 - kino kodi\nNom: Robotar")
    assert p.code == "1"
    assert p.title == "Robotar"


def test_auto_code_kept_as_marker() -> None:
    p = parse_movie_caption("#auto\nNom: Yangi kino")
    assert p.code == "auto"
    assert p.is_complete


def test_kod_key_alias() -> None:
    p = parse_movie_caption("Kod: 55\nName: Movie\nGenre: action")
    assert p.code == "55"
    assert p.title == "Movie"
    assert p.genre == "action"


def test_incomplete_missing_title() -> None:
    p = parse_movie_caption("#1\nJanr: drama")
    assert p.has_markers is True
    assert p.is_complete is False


def test_plain_caption_no_markers() -> None:
    p = parse_movie_caption("Shunchaki oddiy video izohi, hech qanday belgi yo'q")
    assert p.has_markers is False
    assert p.code is None and p.title is None


def test_empty_caption() -> None:
    p = parse_movie_caption(None)
    assert not p.has_markers
    p2 = parse_movie_caption("")
    assert not p2.has_markers


def test_invalid_year_ignored() -> None:
    p = parse_movie_caption("#1\nNom: X\nYil: abcd")
    assert p.year is None
