"""Kanal postidan kinoni AVTO qo'shish.

Admin yopiq (storage) kanalga videoni caption bilan tashlaydi:

    #1
    Nom: Robotar
    Janr: drama

Bot (kanalda admin) postni oladi, caption'ni o'qiydi va kinoni avtomatik
saqlaydi. Post tahrirlansa — mavjud kino yangilanadi.

XAVFSIZLIK: faqat STORAGE_CHANNEL_ID dagi postlar qayta ishlanadi (obuna
kanallaridagi postlar hisobga olinmaydi).

DIAGNOSTIKA: bot qaysi kanaldan post olsa, uning chat_id sini logga yozadi —
shu orqali .env dagi STORAGE_CHANNEL_ID ni to'g'ri qo'yish mumkin.
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.movie_service import MovieService
from app.utils.i18n import t
from app.utils.movie_caption import parse_movie_caption

logger = logging.getLogger(__name__)

router = Router(name="channel_intake")


def _has_media(message: Message) -> bool:
    return bool(message.video or message.document or message.animation)


def _is_storage(message: Message) -> bool:
    """Post storage kanaldanmi? Har doim chat_id ni logga yozadi (diagnostika)."""
    chat = message.chat
    match = chat.id == settings.storage_channel_id
    logger.info(
        "Kanal post: chat_id=%s title=%r  |  STORAGE_CHANNEL_ID=%s  |  moslik=%s",
        chat.id,
        chat.title,
        settings.storage_channel_id,
        match,
    )
    return match


async def _notify_admins(bot: Bot, text: str) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except TelegramAPIError:
            continue


@router.channel_post()
async def intake_new_post(message: Message, session: AsyncSession) -> None:
    """Yangi kanal posti — kinoni yaratadi."""
    if not _is_storage(message):
        return

    if not _has_media(message):
        logger.info("Storage post o'tkazib yuborildi: video/media yo'q.")
        return

    parsed = parse_movie_caption(message.caption or message.text)
    if not parsed.has_markers:
        logger.info(
            "Storage post o'tkazib yuborildi: caption'da kino belgilari yo'q "
            "(#kod / Nom: kutilgan)."
        )
        return

    lang = settings.default_language
    service = MovieService(session)

    code = parsed.code
    if code and code.lower() == "auto":
        code = await service.next_auto_code()

    if not parsed.title or not code:
        logger.warning("Storage post: format to'liq emas (kod yoki nom yo'q).")
        await _notify_admins(message.bot, t("intake_bad_format", lang))
        return

    if await service.code_exists(code):
        logger.warning("Storage post: kod band — %s", code)
        await _notify_admins(message.bot, t("intake_duplicate", lang, code=code))
        return

    movie = await service.add_movie(
        code=code,
        channel_id=message.chat.id,
        message_id=message.message_id,
        title_uz=parsed.title,
        title_ru=None,
        title_en=None,
        year=parsed.year,
        genre=parsed.genre,
    )
    logger.info("Kanaldan kino qo'shildi: kod=%s nom=%r", movie.code, movie.title_uz)
    await _notify_admins(
        message.bot,
        t(
            "intake_added",
            lang,
            code=movie.code,
            title=movie.title_uz,
            genre=movie.genre or t("unknown", lang),
            year=movie.year or t("unknown", lang),
        ),
    )


@router.edited_channel_post()
async def intake_edited_post(message: Message, session: AsyncSession) -> None:
    """Kanal posti tahrirlansa — mavjud kino ma'lumotini yangilaydi."""
    if not _is_storage(message):
        return
    if not _has_media(message):
        return

    parsed = parse_movie_caption(message.caption or message.text)
    if not parsed.has_markers:
        return

    service = MovieService(session)
    existing = await service.get_by_channel_message(
        message.chat.id, message.message_id
    )

    if existing is None:
        # Hali qo'shilmagan bo'lsa — yangi post kabi qo'shamiz
        await intake_new_post(message, session)
        return

    fields: dict[str, object] = {}
    if parsed.title:
        fields["title_uz"] = parsed.title
    if parsed.genre is not None:
        fields["genre"] = parsed.genre
    if parsed.year is not None:
        fields["year"] = parsed.year

    if fields:
        await service.update_fields(existing.id, **fields)
        logger.info("Kanal posti tahrirlandi — kino yangilandi: id=%s", existing.id)
