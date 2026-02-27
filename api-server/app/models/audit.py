import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin


class AuditLog(Base, IdMixin):
    """审计日志模型 — 追加写入，不可修改/删除。

    刻意不继承 TimestampMixin（不需要 updated_at 字段），审计记录一旦写入即为不可变。
    仅使用 created_at 记录操作发生时间。
    """

    __tablename__ = "audit_logs"

    # 刻意不设 ForeignKey 约束：审计日志需长期保留（≥3年），
    # 未来若 hard delete 用户，外键约束会阻止删除或级联丢失审计记录。
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    changes_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    changes_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
