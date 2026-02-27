"""drop foreign key constraint on audit_logs.user_id

审计日志需长期保留（≥3年），外键约束会阻止未来 hard delete 用户。
移除 FK 约束，仅保留 UUID 值和索引。

Revision ID: 004_drop_audit_fk
Revises: 003_email_unique
Create Date: 2026-02-28
"""

from alembic import op

revision = "004_drop_audit_fk"
down_revision = "003_email_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "audit_logs_user_id_fkey", "audit_logs", type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"],
    )
