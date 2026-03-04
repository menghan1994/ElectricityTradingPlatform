"""create market data tables

Revision ID: 010_create_market_data_tables
Revises: 009_create_output_storage_tables
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "010_create_market_data_tables"
down_revision = "009_create_output_storage_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create market_clearing_prices table (timeseries schema, hypertable)
    op.create_table(
        "market_clearing_prices",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trading_date", sa.Date, nullable=False),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column("province", sa.String(50), nullable=False),
        sa.Column("clearing_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'api'"),
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "import_job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_import_jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", "trading_date"),
        sa.CheckConstraint(
            "period >= 1 AND period <= 96",
            name="ck_market_clearing_prices_period",
        ),
        sa.CheckConstraint(
            "source IN ('api', 'manual_import')",
            name="ck_market_clearing_prices_source",
        ),
        sa.UniqueConstraint(
            "province",
            "trading_date",
            "period",
            name="uq_market_clearing_prices_province_date_period",
        ),
        schema="timeseries",
    )
    op.create_index(
        "ix_market_clearing_prices_province_date",
        "market_clearing_prices",
        ["province", "trading_date"],
        schema="timeseries",
    )
    op.create_index(
        "ix_market_clearing_prices_import_job",
        "market_clearing_prices",
        ["import_job_id"],
        schema="timeseries",
    )
    op.execute(
        "SELECT create_hypertable('timeseries.market_clearing_prices', 'trading_date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE)"
    )

    # 2. Create market_data_sources table (public schema)
    op.create_table(
        "market_data_sources",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("province", sa.String(50), nullable=False, unique=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("api_endpoint", sa.String(500), nullable=True),
        sa.Column("api_key_encrypted", sa.LargeBinary, nullable=True),
        sa.Column(
            "api_auth_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'api_key'"),
        ),
        sa.Column(
            "fetch_schedule",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'0 7,12,17 * * *'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_fetch_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("last_fetch_error", sa.Text, nullable=True),
        sa.Column(
            "cache_ttl_seconds",
            sa.Integer,
            nullable=False,
            server_default=sa.text("3600"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "api_auth_type IN ('api_key', 'bearer', 'none')",
            name="ck_market_data_sources_auth_type",
        ),
        sa.CheckConstraint(
            "last_fetch_status IN ('pending', 'success', 'failed')",
            name="ck_market_data_sources_fetch_status",
        ),
        sa.CheckConstraint(
            "cache_ttl_seconds > 0",
            name="ck_market_data_sources_cache_ttl",
        ),
    )

    # 3. Update data_import_jobs import_type constraint to include 'market_data'
    op.drop_constraint("ck_data_import_jobs_import_type", "data_import_jobs", type_="check")
    op.create_check_constraint(
        "ck_data_import_jobs_import_type",
        "data_import_jobs",
        "import_type IN ('trading_data', 'station_output', 'storage_operation', 'market_data')",
    )


def downgrade() -> None:
    # Restore original import_type constraint
    op.drop_constraint("ck_data_import_jobs_import_type", "data_import_jobs", type_="check")
    op.create_check_constraint(
        "ck_data_import_jobs_import_type",
        "data_import_jobs",
        "import_type IN ('trading_data', 'station_output', 'storage_operation')",
    )

    # Drop market_data_sources
    op.drop_table("market_data_sources")

    # Drop market_clearing_prices
    op.drop_index(
        "ix_market_clearing_prices_import_job",
        table_name="market_clearing_prices",
        schema="timeseries",
    )
    op.drop_index(
        "ix_market_clearing_prices_province_date",
        table_name="market_clearing_prices",
        schema="timeseries",
    )
    op.drop_table("market_clearing_prices", schema="timeseries")
