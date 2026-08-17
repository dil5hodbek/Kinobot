"""Admin statistika paneli."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stats_service import StatsService
from app.utils.filters import ButtonText, IsAdmin

router = Router(name="admin_stats")
router.message.filter(IsAdmin())


@router.message(StateFilter(None), ButtonText("btn_stats"))
async def show_stats(message: Message, lang: str, session: AsyncSession) -> None:
    service = StatsService(session)
    stats = await service.collect()
    await message.answer(service.format_report(stats, lang))
