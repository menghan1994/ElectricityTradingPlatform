"""add role, email columns to users and create audit_logs table

Revision ID: 002_add_role_email_audit
Revises: 001_create_users
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002_add_role_email_audit"
down_revision = "001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users 表添加 role 列
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(32),
            nullable=False,
            server_default="trader",
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'trader', 'storage_operator', 'trading_manager', 'executive_readonly')",
    )

    # 2. users 表添加 email 列
    op.add_column(
        "users",
        sa.Column("email", sa.String(128), nullable=True),
    )

    # 3. 创建 audit_logs 表
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
        sa.Column("changes_before", JSONB, nullable=True),
        sa.Column("changes_after", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_resource_type_resource_id", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type_resource_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_column("users", "email")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
