"""Inline klaviaturalar: til, obuna, natijalar, trend, admin."""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.models.movie import Movie
from app.utils.format import movie_title
from app.utils.i18n import t

if TYPE_CHECKING:
    from app.services.subscription_service import ChannelInfo


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek", callback_data="lang:uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.adjust(3)
    return builder.as_markup()


def subscription_keyboard(
    channels: list["ChannelInfo"], lang: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(
            InlineKeyboardButton(text=f"{ch.display} ➕", url=ch.url)
        )
    builder.row(
        InlineKeyboardButton(
            text=t("subscribe_check", lang), callback_data="check_subscription"
        )
    )
    return builder.as_markup()


def channels_list_keyboard(
    channels_status: list[tuple["ChannelInfo", bool]],
) -> InlineKeyboardMarkup:
    """Har bir kanal oldida obuna holati belgisi: ✅ (a'zo) yoki ➕ (qo'shilish)."""
    builder = InlineKeyboardBuilder()
    for ch, subscribed in channels_status:
        mark = "✅" if subscribed else "➕"
        builder.row(InlineKeyboardButton(text=f"{mark} {ch.display}", url=ch.url))
    return builder.as_markup()


def search_results_keyboard(movies: list[Movie], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        title = movie_title(movie, lang)
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {title}", callback_data=f"movie:{movie.id}"
            )
        )
    return builder.as_markup()


def trend_keyboard(movies: list[Movie], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, movie in enumerate(movies, start=1):
        title = movie_title(movie, lang)
        label = f"{idx}. {title} ({t('views_label', lang)} {movie.views_count})"
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"movie:{movie.id}")
        )
    return builder.as_markup()


def genre_movies_keyboard(movies: list[Movie], lang: str) -> InlineKeyboardMarkup:
    """Janr bo'yicha topilgan kinolar — mavjud `movie:{id}` callback'ini ishlatadi."""
    builder = InlineKeyboardBuilder()
    for movie in movies:
        title = movie_title(movie, lang)
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {title} — {movie.code}", callback_data=f"movie:{movie.id}"
            )
        )
    return builder.as_markup()


def movie_link_keyboard(url: str, lang: str) -> InlineKeyboardMarkup:
    """Link-manba kino uchun — video o'rniga havola tugmasi + reklama tugmalari."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t("btn_watch_movie", lang), url=url))
    builder.attach(InlineKeyboardBuilder.from_markup(promo_keyboard(lang)))
    return builder.as_markup()


def promo_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Har bir yuborilgan kino ostiga qo'shiladi: botga va kanalga havola
    (kino xabari forward qilinsa ham, oluvchi botni/kanalni osongina topsin)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("promo_btn_bot", lang),
            url=f"https://t.me/{settings.promo_bot_username}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("promo_btn_channel", lang),
            url=f"https://t.me/{settings.promo_channel_username}",
        )
    )
    return builder.as_markup()


def clear_chat_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    """"Suhbatni tozalash" — tasdiqlash/orqaga."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_clear_chat_yes", lang), callback_data="clearchat_confirm")
    builder.button(text=t("btn_clear_chat_back", lang), callback_data="clearchat_cancel")
    builder.adjust(2)
    return builder.as_markup()


# === ADMIN ===

def add_movie_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_save", lang), callback_data="movie_save")
    builder.button(text=t("btn_cancel", lang), callback_data="movie_cancel")
    builder.adjust(2)
    return builder.as_markup()


def skip_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_skip", lang), callback_data="fsm_skip")
    return builder.as_markup()


def add_link_movie_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    """add_movie_confirm_keyboard bilan bir xil ko'rinish, lekin alohida
    callback nomi — link va kanal oqimlari FSM holati bilan ajralган bo'lsa
    ham, o'qishda chalkashmasin uchun."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_save", lang), callback_data="link_movie_save")
    builder.button(text=t("btn_cancel", lang), callback_data="link_movie_cancel")
    builder.adjust(2)
    return builder.as_markup()


def broadcast_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_broadcast_send", lang), callback_data="broadcast_send")
    builder.button(text=t("btn_cancel", lang), callback_data="broadcast_cancel")
    builder.adjust(2)
    return builder.as_markup()


def delete_results_keyboard(movies: list[Movie], lang: str) -> InlineKeyboardMarkup:
    """Nom bo'yicha bir nechta natija — o'chirish uchun kinoni tanlash."""
    builder = InlineKeyboardBuilder()
    for movie in movies:
        title = movie_title(movie, lang)
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {title} — {movie.code}",
                callback_data=f"delpick:{movie.id}",
            )
        )
    return builder.as_markup()


def delete_confirm_keyboard(movie_id: int, lang: str) -> InlineKeyboardMarkup:
    """Tanlangan kinoni o'chirishni tasdiqlash."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_delete_yes", lang), callback_data=f"delyes:{movie_id}")
    builder.button(text=t("btn_delete_no", lang), callback_data="delno")
    builder.adjust(2)
    return builder.as_markup()


def edit_movie_keyboard(movie: Movie, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_edit_title", lang), callback_data=f"edit:title:{movie.id}")
    builder.button(text=t("btn_edit_year", lang), callback_data=f"edit:year:{movie.id}")
    builder.button(text=t("btn_edit_genre", lang), callback_data=f"edit:genre:{movie.id}")
    if movie.source_type == "link":
        builder.button(text=t("btn_edit_url", lang), callback_data=f"edit:url:{movie.id}")
        builder.adjust(2, 2)
    else:
        builder.adjust(2, 1)
    return builder.as_markup()
