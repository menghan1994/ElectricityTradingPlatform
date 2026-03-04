"""create station output and storage operation tables

Revision ID: 009_create_output_storage_tables
Revises: 008_data_import_infrastructure
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "009_create_output_storage_tables"
down_revision = "008_data_import_infrastructure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add import_type column to data_import_jobs
    op.add_column(
        "data_import_jobs",
        sa.Column(
            "import_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'trading_data'"),
        ),
    )
    op.create_index("ix_data_import_jobs_import_type", "data_import_jobs", ["import_type"])

    # Add import_type check constraint
    op.create_check_constraint(
        "ck_data_import_jobs_import_type",
        "data_import_jobs",
        "import_type IN ('trading_data', 'station_output', 'storage_operation')",
    )

    # 1b. Add ems_format column to data_import_jobs (nullable, only used for storage_operation)
    op.add_column(
        "data_import_jobs",
        sa.Column("ems_format", sa.String(20), nullable=True),
    )

    # 2. Add current_soc column to storage_devices (with range constraint)
    op.add_column(
        "storage_devices",
        sa.Column("current_soc", sa.Numeric(5, 4), nullable=True),
    )
    op.create_check_constraint(
        "ck_storage_devices_current_soc_range",
        "storage_devices",
        "current_soc IS NULL OR (current_soc >= 0 AND current_soc <= 1)",
    )

    # 3. Create station_output_records table (timeseries schema, hypertable)
    op.create_table(
        "station_output_records",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trading_date", sa.Date, nullable=False),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column(
            "station_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("power_stations.id"),
            nullable=False,
        ),
        sa.Column("actual_output_kw", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "import_job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_import_jobs.id"),
            nullable=False,
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
            name="ck_station_output_records_period",
        ),
        sa.CheckConstraint(
            "actual_output_kw >= 0",
            name="ck_station_output_records_output_kw",
        ),
        sa.UniqueConstraint(
            "station_id",
            "trading_date",
            "period",
            name="uq_station_output_records_station_date_period",
        ),
        schema="timeseries",
    )
    op.create_index(
        "ix_station_output_records_station_date",
        "station_output_records",
        ["station_id", "trading_date"],
        schema="timeseries",
    )
    op.create_index(
        "ix_station_output_records_import_job",
        "station_output_records",
        ["import_job_id"],
        schema="timeseries",
    )
    op.execute(
        "SELECT create_hypertable('timeseries.station_output_records', 'trading_date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE)"
    )

    # 4. Create storage_operation_records table (timeseries schema, hypertable)
    op.create_table(
        "storage_operation_records",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trading_date", sa.Date, nullable=False),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column(
            "device_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storage_devices.id"),
            nullable=False,
        ),
        sa.Column("soc", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "charge_power_kw",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "discharge_power_kw",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "cycle_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "import_job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_import_jobs.id"),
            nullable=False,
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
            name="ck_storage_operation_records_period",
        ),
        sa.CheckConstraint(
            "soc >= 0 AND soc <= 1",
            name="ck_storage_operation_records_soc",
        ),
        sa.CheckConstraint(
            "charge_power_kw >= 0",
            name="ck_storage_operation_records_charge",
        ),
        sa.CheckConstraint(
            "discharge_power_kw >= 0",
            name="ck_storage_operation_records_discharge",
        ),
        sa.CheckConstraint(
            "cycle_count >= 0",
            name="ck_storage_operation_records_cycle",
        ),
        sa.UniqueConstraint(
            "device_id",
            "trading_date",
            "period",
            name="uq_storage_operation_records_device_date_period",
        ),
        schema="timeseries",
    )
    op.create_index(
        "ix_storage_operation_records_device_date",
        "storage_operation_records",
        ["device_id", "trading_date"],
        schema="timeseries",
    )
    op.create_index(
        "ix_storage_operation_records_import_job",
        "storage_operation_records",
        ["import_job_id"],
        schema="timeseries",
    )
    op.execute(
        "SELECT create_hypertable('timeseries.storage_operation_records', 'trading_date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    # Drop storage_operation_records
    op.drop_index(
        "ix_storage_operation_records_import_job",
        table_name="storage_operation_records",
        schema="timeseries",
    )
    op.drop_index(
        "ix_storage_operation_records_device_date",
        table_name="storage_operation_records",
        schema="timeseries",
    )
    op.drop_table("storage_operation_records", schema="timeseries")

    # Drop station_output_records
    op.drop_index(
        "ix_station_output_records_import_job",
        table_name="station_output_records",
        schema="timeseries",
    )
    op.drop_index(
        "ix_station_output_records_station_date",
        table_name="station_output_records",
        schema="timeseries",
    )
    op.drop_table("station_output_records", schema="timeseries")

    # Remove current_soc constraint and column from storage_devices
    op.drop_constraint("ck_storage_devices_current_soc_range", "storage_devices", type_="check")
    op.drop_column("storage_devices", "current_soc")

    # Remove ems_format from data_import_jobs
    op.drop_column("data_import_jobs", "ems_format")

    # Remove import_type from data_import_jobs
    op.drop_constraint("ck_data_import_jobs_import_type", "data_import_jobs", type_="check")
    op.drop_index("ix_data_import_jobs_import_type", table_name="data_import_jobs")
    op.drop_column("data_import_jobs", "import_type")
