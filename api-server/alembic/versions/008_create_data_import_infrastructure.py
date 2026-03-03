"""create data import infrastructure

数据导入基础设施：data_import_jobs、timeseries.trading_records（TimescaleDB 超表）、import_anomalies。
支撑历史交易数据批量导入与质量校验功能（Story 2.3）。

Revision ID: 008_data_import_infrastructure
Revises: 007_province_market_rules
Create Date: 2026-03-01
"""

import sqlalchemy as sa
from alembic import op

revision = "008_data_import_infrastructure"
down_revision = "007_province_market_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # timeseries schema 和 TimescaleDB 扩展由 scripts/init-db.sh 初始化，
    # 无需在 migration 中重复创建（app_user 角色无 CREATE SCHEMA / EXTENSION 权限）。

    # 创建 data_import_jobs 表（public schema）
    op.create_table(
        "data_import_jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("station_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("power_stations.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_records", sa.Integer, server_default=sa.text("0")),
        sa.Column("processed_records", sa.Integer, server_default=sa.text("0")),
        sa.Column("success_records", sa.Integer, server_default=sa.text("0")),
        sa.Column("failed_records", sa.Integer, server_default=sa.text("0")),
        sa.Column("data_completeness", sa.Numeric(5, 2), server_default=sa.text("0")),
        sa.Column("last_processed_row", sa.Integer, server_default=sa.text("0")),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_data_import_jobs_status",
        ),
    )

    # data_import_jobs 索引
    op.create_index("ix_data_import_jobs_station", "data_import_jobs", ["station_id"])
    op.create_index("ix_data_import_jobs_status", "data_import_jobs", ["status"])

    # 创建 trading_records 表（timeseries schema）
    # TimescaleDB 超表要求分区列 trading_date 包含在主键中，因此使用复合主键 (id, trading_date)
    op.create_table(
        "trading_records",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("trading_date", sa.Date, nullable=False),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column("station_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("power_stations.id"), nullable=False),
        sa.Column("clearing_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("import_job_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("data_import_jobs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", "trading_date"),
        sa.CheckConstraint("period >= 1 AND period <= 96", name="ck_trading_records_period"),
        sa.UniqueConstraint("station_id", "trading_date", "period", name="uq_trading_records_station_date_period"),
        schema="timeseries",
    )

    # trading_records 索引
    op.create_index(
        "ix_trading_records_station_date",
        "trading_records",
        ["station_id", "trading_date"],
        schema="timeseries",
    )

    # 将 trading_records 转换为 TimescaleDB 超表
    op.execute(
        "SELECT create_hypertable('timeseries.trading_records', 'trading_date', "
        "chunk_time_interval => INTERVAL '1 month')"
    )

    # 创建 import_anomalies 表（public schema）
    op.create_table(
        "import_anomalies",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("import_job_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("data_import_jobs.id"), nullable=False),
        sa.Column("row_number", sa.Integer, nullable=False),
        sa.Column("anomaly_type", sa.String(20), nullable=False),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("raw_value", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "anomaly_type IN ('missing', 'format_error', 'out_of_range', 'duplicate')",
            name="ck_import_anomalies_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed_normal', 'corrected', 'deleted')",
            name="ck_import_anomalies_status",
        ),
    )

    # import_anomalies 索引
    op.create_index("ix_import_anomalies_job_id", "import_anomalies", ["import_job_id"])
    op.create_index("ix_import_anomalies_type", "import_anomalies", ["anomaly_type"])


def downgrade() -> None:
    op.drop_index("ix_import_anomalies_type", table_name="import_anomalies")
    op.drop_index("ix_import_anomalies_job_id", table_name="import_anomalies")
    op.drop_table("import_anomalies")

    op.drop_index("ix_trading_records_station_date", table_name="trading_records", schema="timeseries")
    op.drop_table("trading_records", schema="timeseries")

    op.drop_index("ix_data_import_jobs_status", table_name="data_import_jobs")
    op.drop_index("ix_data_import_jobs_station", table_name="data_import_jobs")
    op.drop_table("data_import_jobs")
