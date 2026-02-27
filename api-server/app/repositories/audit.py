from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


MAX_AUDIT_QUERY_LIMIT = 500


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def delete(self, entity: AuditLog) -> None:
        raise NotImplementedError("审计日志不允许删除")

    async def get_by_resource(
        self, resource_type: str, resource_id: UUID, skip: int = 0, limit: int = 50,
    ) -> list[AuditLog]:
        limit = min(limit, MAX_AUDIT_QUERY_LIMIT)
        stmt = (
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 50,
    ) -> list[AuditLog]:
        limit = min(limit, MAX_AUDIT_QUERY_LIMIT)
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
