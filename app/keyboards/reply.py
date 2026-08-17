"""Reply klaviaturalar: asosiy menyu va admin menyu."""
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
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_add_movie", lang)),
                KeyboardButton(text=t("btn_edit_movie", lang)),
            ],
            [
                KeyboardButton(text=t("btn_delete_movie", lang)),
                KeyboardButton(text=t("btn_stats", lang)),
            ],
            [
                KeyboardButton(text=t("btn_broadcast", lang)),
                KeyboardButton(text=t("btn_add_channel", lang)),
            ],
            [
                KeyboardButton(text=t("btn_codes", lang)),
                KeyboardButton(text=t("btn_exit", lang)),
            ],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
