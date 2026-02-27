from typing import Any
from uuid import UUID

import structlog

from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository

logger = structlog.get_logger()


class AuditService:
    """审计日志服务 — 追加写入，不可修改。

    设计决策：审计日志与业务操作共享同一 DB session（事务）。
    这意味着审计写入失败会导致业务操作一起回滚。这是有意设计：
    - 优先保证审计完整性（每个敏感操作必须有对应的审计记录）
    - 如果审计日志无法写入，业务操作也不应生效（合规要求）
    - 权衡：极端情况下审计表空间不足可能阻塞业务操作
    - 未来如需解耦，可改为异步消息队列投递（但需接受审计延迟和丢失风险）
    """

    def __init__(self, audit_repo: AuditLogRepository):
        self.audit_repo = audit_repo

    async def log_action(
        self,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        changes_before: dict[str, Any] | None = None,
        changes_after: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes_before=changes_before,
            changes_after=changes_after,
            ip_address=ip_address,
        )
        created = await self.audit_repo.create(log_entry)
        logger.info(
            "audit_log_created",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            user_id=str(user_id),
        )
        return created
