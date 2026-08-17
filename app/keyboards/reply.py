"""Reply klaviaturalar: asosiy menyu va 2 qavatli admin menyu.

Admin menyusi HUB + 2 submenu qilib qurilgan (8 tugmani bitta ekranga
tiqishtirish o'rniga): `admin_menu_keyboard` — hub (4 tugma), undan
"🎬 Kinolar" / "📊 Boshqaruv" bosilsa mos submenu ochiladi, har birida
"🔙 Orqaga" bilan hubga qaytish bor. Mavjud tugma-triggerли handlerlarning
(btn_add_movie va h.k.) BIRONTASIGA tegilmagan — faqat qaysi ekranda
qaysi tugma ko'rinishi o'zgardi.
"""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.utils.i18n import t


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_search", lang)),
                KeyboardButton(text=t("btn_channels", lang)),
            ],
            [
                KeyboardButton(text=t("btn_trend", lang)),
                KeyboardButton(text=t("btn_language", lang)),
            ],
            [
                KeyboardButton(text=t("btn_clear_chat", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Admin HUB — bo'lim tanlaydi, aniq amal emas."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_movies_menu", lang)),
                KeyboardButton(text=t("btn_management_menu", lang)),
            ],
            [
                KeyboardButton(text=t("btn_user_menu", lang)),
                KeyboardButton(text=t("btn_exit", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def admin_movies_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """"🎬 Kinolar" submenu — kino bilan bog'liq barcha amallar."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_add_movie", lang)),
                KeyboardButton(text=t("btn_add_link_movie", lang)),
            ],
            [
                KeyboardButton(text=t("btn_edit_movie", lang)),
                KeyboardButton(text=t("btn_delete_movie", lang)),
            ],
            [
                KeyboardButton(text=t("btn_codes", lang)),
                KeyboardButton(text=t("btn_back", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def admin_management_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """"📊 Boshqaruv" submenu — statistika, reklama, kanal, trend."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_stats", lang)),
                KeyboardButton(text=t("btn_broadcast", lang)),
            ],
            [
                KeyboardButton(text=t("btn_add_channel", lang)),
                KeyboardButton(text=t("btn_trend_movies", lang)),
            ],
            [
                KeyboardButton(text=t("btn_back", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
