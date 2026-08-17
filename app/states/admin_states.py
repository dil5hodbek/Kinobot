"""Admin FSM holatlari."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddMovie(StatesGroup):
    waiting_forward = State()
    waiting_code = State()
    waiting_title_uz = State()
    waiting_title_ru = State()
    waiting_title_en = State()
    waiting_year = State()
    waiting_genre = State()
    waiting_confirm = State()


class AddLinkMovie(StatesGroup):
    """AddMovie bilan bir xil oqim — faqat 1-qadam forward o'rniga URL."""

    waiting_url = State()
    waiting_code = State()
    waiting_title_uz = State()
    waiting_title_ru = State()
    waiting_title_en = State()
    waiting_year = State()
    waiting_genre = State()
    waiting_confirm = State()


class Broadcast(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()


class AddChannel(StatesGroup):
    waiting_username = State()


class EditMovie(StatesGroup):
    waiting_code = State()
    choosing_field = State()
    waiting_value = State()


class DeleteMovie(StatesGroup):
    waiting_query = State()
