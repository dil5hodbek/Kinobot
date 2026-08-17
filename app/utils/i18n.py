"""Lokalizatsiya (i18n): locale fayllarini yuklaydi va matn qaytaradi."""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = ("uz", "ru", "en")
_LOCALES_DIR = Path(__file__).resolve().parent.parent.parent / "locales"

_translations: dict[str, dict[str, str]] = {}


def load_translations() -> None:
    """Barcha locale JSON fayllarini xotiraga yuklaydi."""
    for lang in SUPPORTED_LANGUAGES:
        path = _LOCALES_DIR / f"{lang}.json"
        try:
            with path.open("r", encoding="utf-8") as fp:
                _translations[lang] = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Locale faylini yuklab bo'lmadi: %s (%s)", path, exc)
            _translations[lang] = {}


def t(key: str, lang: str = "uz", /, **kwargs: object) -> str:
    """Kalit bo'yicha tarjimani qaytaradi va {placeholder}'larni to'ldiradi.

    Til topilmasa 'uz'ga, kalit topilmasa kalitning o'ziga qaytadi.
    """
    if not _translations:
        load_translations()

    lang = lang if lang in _translations else "uz"
    template = _translations.get(lang, {}).get(key)
    if template is None:
        # uz'dan zaxira sifatida qidiramiz
        template = _translations.get("uz", {}).get(key, key)

    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template
    return template


def all_labels(key: str) -> set[str]:
    """Berilgan kalitning barcha tillardagi qiymatlari (tugma matnini aniqlash uchun)."""
    if not _translations:
        load_translations()
    labels: set[str] = set()
    for lang in SUPPORTED_LANGUAGES:
        value = _translations.get(lang, {}).get(key)
        if value:
            labels.add(value)
    return labels


def button_matches(text: str | None, key: str) -> bool:
    """Matn shu i18n kalitining istalgan tildagi qiymatiga tengmi?"""
    if not text:
        return False
    return text in all_labels(key)
