"""create prediction model tables

Revision ID: 011_create_prediction_model_tables
Revises: 010_create_market_data_tables
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op

revision = "011_create_prediction_model_tables"
down_revision = "010_create_market_data_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create prediction_models table (public schema)
    op.create_table(
        "prediction_models",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "station_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("power_stations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column(
            "model_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'wind'"),
        ),
        sa.Column("api_endpoint", sa.String(500), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary, nullable=True),
        sa.Column(
            "api_auth_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'api_key'"),
        ),
        sa.Column(
            "call_frequency_cron",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'0 6,12 * * *'"),
        ),
        sa.Column(
            "timeout_seconds",
            sa.Integer,
            nullable=False,
            server_default=sa.text("30"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'disabled'"),
        ),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_check_status", sa.String(20), nullable=True),
        sa.Column("last_check_error", sa.Text, nullable=True),
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
            "model_type IN ('wind', 'solar', 'hybrid')",
            name="ck_prediction_models_model_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'error', 'disabled')",
            name="ck_prediction_models_status",
        ),
        sa.CheckConstraint(
            "api_auth_type IN ('api_key', 'bearer', 'none')",
            name="ck_prediction_models_auth_type",
        ),
    )
    op.create_index(
        "ix_prediction_models_station_id",
        "prediction_models",
        ["station_id"],
    )

    # 2. Create power_predictions table (timeseries schema, hypertable)
    op.create_table(
        "power_predictions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("prediction_date", sa.Date, nullable=False),
        sa.Column("period", sa.Integer, nullable=False),
        sa.Column(
            "station_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("power_stations.id"),
            nullable=False,
        ),
        sa.Column(
            "model_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prediction_models.id"),
            nullable=False,
        ),
        sa.Column("predicted_power_kw", sa.Numeric(12, 2), nullable=False),
        sa.Column("confidence_upper_kw", sa.Numeric(12, 2), nullable=False),
        sa.Column("confidence_lower_kw", sa.Numeric(12, 2), nullable=False),
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
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", "prediction_date"),
        sa.UniqueConstraint(
            "station_id",
            "prediction_date",
            "period",
            "model_id",
            name="uq_power_predictions_station_date_period_model",
        ),
        sa.CheckConstraint(
            "period >= 1 AND period <= 96",
            name="ck_power_predictions_period",
        ),
        sa.CheckConstraint(
            "confidence_upper_kw >= predicted_power_kw AND predicted_power_kw >= confidence_lower_kw",
            name="ck_power_predictions_confidence",
        ),
        schema="timeseries",
    )
    op.create_index(
        "ix_power_predictions_station_date",
        "power_predictions",
        ["station_id", "prediction_date"],
        schema="timeseries",
    )
    op.execute(
        "SELECT create_hypertable('timeseries.power_predictions', 'prediction_date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    # Drop power_predictions
    op.drop_index(
        "ix_power_predictions_station_date",
        table_name="power_predictions",
        schema="timeseries",
    )
    op.drop_table("power_predictions", schema="timeseries")

    # Drop prediction_models
    op.drop_index(
        "ix_prediction_models_station_id",
        table_name="prediction_models",
    )
    op.drop_table("prediction_models")
