"""Kanal post caption'idan kino ma'lumotlarini ajratib olish.

Qo'llab-quvvatlanadigan format (satrlar tartibi ahamiyatsiz):

    #1
    Nom: Robotar
    Janr: drama
    Yil: 2024

  • `#<kod>`  yoki  `Kod: <kod>`  → kino kodi (`#auto` → avto raqam)
  • `Nom:` / `Nomi:` / `Name:` / `Title:` / `Название:`  → kino nomi
  • `Janr:` / `Janri:` / `Genre:` / `Жанр:`  → janr (ixtiyoriy)
  • `Yil:` / `Year:` / `Год:`  → yil (ixtiyoriy)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_CODE_HASH = re.compile(r"^#\s*([A-Za-z0-9_-]{1,20})")

_TITLE_KEYS = {"nom", "nomi", "name", "title", "название", "kino"}
_GENRE_KEYS = {"janr", "janri", "genre", "жанр"}
_YEAR_KEYS = {"yil", "yili", "year", "год"}
_CODE_KEYS = {"kod", "kodi", "code", "код"}

_MAX_TITLE = 255
_MAX_GENRE = 100
_MAX_CODE = 20


@dataclass(slots=True)
class ParsedMovie:
    code: str | None = None
    title: str | None = None
    genre: str | None = None
    year: int | None = None
    has_markers: bool = False  # caption umuman "kino posti"ga o'xshaydimi

    @property
    def is_complete(self) -> bool:
        """Kino yaratish uchun minimal (kod + nom) bormi?"""
        return bool(self.code and self.title)


def parse_movie_caption(text: str | None) -> ParsedMovie:
    """Caption matnidan ParsedMovie qaytaradi (topilmasa bo'sh, has_markers=False)."""
    result = ParsedMovie()
    if not text:
        return result

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # 1) `#kod` ko'rinishi
        if result.code is None:
            m = _CODE_HASH.match(line)
            if m:
                result.code = m.group(1)[:_MAX_CODE]
                result.has_markers = True
                continue

        # 2) `Kalit: qiymat` ko'rinishi
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key_norm = key.strip().lower().replace(" ", "")
        value = value.strip()
        if not value:
            continue

        if key_norm in _TITLE_KEYS:
            if result.title is None:
                result.title = value[:_MAX_TITLE]
                result.has_markers = True
        elif key_norm in _GENRE_KEYS:
            if result.genre is None:
                result.genre = value[:_MAX_GENRE]
        elif key_norm in _YEAR_KEYS:
            if result.year is None and value.isdigit() and 1900 <= int(value) <= 2100:
                result.year = int(value)
        elif key_norm in _CODE_KEYS:
            if result.code is None:
                token = value.split()[0] if value else ""
                if token:
                    result.code = token[:_MAX_CODE]
                    result.has_markers = True

    return result
