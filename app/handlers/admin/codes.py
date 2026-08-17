"""Admin: '📋 Kodlar' — barcha kinolarni Excel (.xlsx) faylga chiqarish."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.movie_service import MovieService
from app.services.report_service import build_movies_workbook
from app.utils.filters import ButtonText, IsAdmin
from app.utils.i18n import t

logger = logging.getLogger(__name__)

router = Router(name="admin_codes")
router.message.filter(IsAdmin())


@router.message(StateFilter(None), ButtonText("btn_codes"))
async def export_codes(message: Message, lang: str, session: AsyncSession) -> None:
    service = MovieService(session)
    movies = await service.get_all_movies()

    if not movies:
        await message.answer(t("report_empty", lang))
        return

    status = await message.answer(t("report_generating", lang))

    try:
        # openpyxl sinxron — event loop bloklanmasligi uchun alohida threadda
        data = await asyncio.to_thread(build_movies_workbook, movies, lang)
    except Exception as exc:  # noqa: BLE001 - foydalanuvchiga tushunarli xato
        logger.exception("Excel yaratishda xatolik: %s", exc)
        await message.answer(t("report_error", lang))
        return
    finally:
        try:
            await status.delete()
        except TelegramAPIError:
            pass

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"kino_kodlari_{date_str}.xlsx"
    document = BufferedInputFile(data, filename=filename)

    try:
        await message.answer_document(
            document,
            caption=t("report_caption", lang, count=len(movies), date=date_str),
        )
    except TelegramAPIError as exc:
        logger.warning("Excel yuborib bo'lmadi: %s", exc)
        await message.answer(t("report_error", lang))
