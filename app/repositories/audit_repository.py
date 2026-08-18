"""Admin audit log repository."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit_log import AdminAuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        admin_id: int,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        metadata: str | None = None,
    ) -> None:
        self._session.add(
            AdminAuditLog(
                admin_id=admin_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_=metadata,
            )
        )
