"""Admin amallarini audit qilish ("kim nimani qachon qildi").

Har bir admin mutatsiyasi (kino qo'shish/tahrirlash/o'chirish, trend,
kanal, broadcast) shu yerdan o'tadi — muammo chiqqanda javob darhol topiladi.
Yozuv request sessiyasida qo'shiladi (middleware oxirida commit bo'ladi),
asosiy amal bilan bitta tranzaksiyada — amal rollback bo'lsa audit ham
yozilmaydi (yolg'on audit qolmaydi).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository


async def audit(
    session: AsyncSession,
    *,
    admin_id: int,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    metadata: str | None = None,
) -> None:
    await AuditRepository(session).record(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        metadata=metadata,
    )
