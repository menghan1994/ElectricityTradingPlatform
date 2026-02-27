"""add unique constraint to users.email

Revision ID: 003_email_unique
Revises: 002_add_role_email_audit
Create Date: 2026-02-27
"""

from alembic import op

revision = "003_email_unique"
down_revision = "002_add_role_email_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
