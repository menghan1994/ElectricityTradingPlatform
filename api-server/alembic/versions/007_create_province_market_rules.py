"""create province_market_rules table

省份市场规则表，存储各省份的限价范围、结算方式和偏差考核公式配置。
支撑省份市场规则配置功能（Story 2.2）。

Revision ID: 007_province_market_rules
Revises: 006_station_grid_device_battery
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op

revision = "007_province_market_rules"
down_revision = "006_station_grid_device_battery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "province_market_rules",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("province", sa.String(50), nullable=False, unique=True),
        sa.Column("price_cap_upper", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_cap_lower", sa.Numeric(10, 2), nullable=False),
        sa.Column("settlement_method", sa.String(20), nullable=False),
        sa.Column("deviation_formula_type", sa.String(20), nullable=False),
        sa.Column("deviation_formula_params", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("price_cap_upper > price_cap_lower", name="ck_province_market_rules_price_cap"),
        sa.CheckConstraint("price_cap_upper > 0 AND price_cap_lower >= 0", name="ck_province_market_rules_price_positive"),
        sa.CheckConstraint("settlement_method IN ('spot', 'contract', 'hybrid')", name="ck_province_market_rules_settlement"),
        sa.CheckConstraint("deviation_formula_type IN ('stepped', 'proportional', 'bandwidth')", name="ck_province_market_rules_deviation_type"),
    )


def downgrade() -> None:
    op.drop_table("province_market_rules")
