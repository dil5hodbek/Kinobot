"""i18n testlari: kalit parity, formatlash, tugma aniqlash."""
from __future__ import annotations

from app.utils.i18n import (
    SUPPORTED_LANGUAGES,
    all_labels,
    button_matches,
    load_translations,
    t,
)


def test_all_languages_have_same_keys() -> None:
    load_translations()
    from app.utils import i18n

    keys = {lang: set(i18n._translations[lang].keys()) for lang in SUPPORTED_LANGUAGES}
    base = keys["uz"]
    for lang in ("ru", "en"):
        assert keys[lang] == base, f"{lang} kalitlari uz bilan mos emas"


def test_t_formats_placeholders() -> None:
    text = t("movie_caption", "uz", title="X", year=2024, genre="G", code="777", views=5)
    assert "X" in text and "777" in text and "2024" in text


def test_t_unknown_key_returns_key() -> None:
    assert t("no_such_key_123", "uz") == "no_such_key_123"


def test_t_falls_back_to_uz_for_unknown_lang() -> None:
    assert t("subscribe_check", "xx") == t("subscribe_check", "uz")


def test_button_matches_across_languages() -> None:
    for lang in SUPPORTED_LANGUAGES:
        assert button_matches(t("btn_search", lang), "btn_search")
    assert not button_matches("tasodifiy matn", "btn_search")


def test_all_labels_returns_three() -> None:
    assert len(all_labels("btn_trend")) == len(SUPPORTED_LANGUAGES)
