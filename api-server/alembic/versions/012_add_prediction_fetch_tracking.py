"""add prediction fetch tracking columns

Revision ID: 012_add_prediction_fetch_tracking
Revises: 011_create_prediction_model_tables
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "012_add_prediction_fetch_tracking"
down_revision = "011_create_prediction_model_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prediction_models",
        sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "prediction_models",
        sa.Column("last_fetch_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "prediction_models",
        sa.Column("last_fetch_error", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prediction_models", "last_fetch_error")
    op.drop_column("prediction_models", "last_fetch_status")
    op.drop_column("prediction_models", "last_fetch_at")
