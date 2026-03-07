import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class PredictionModel(Base, IdMixin, TimestampMixin):
    """功率预测模型配置 - 电站级绑定，管理预测模型接入参数和运行状态。"""

    __tablename__ = "prediction_models"
    __table_args__ = (
        Index("ix_prediction_models_station_id", "station_id"),
        CheckConstraint(
            "model_type IN ('wind', 'solar', 'hybrid')",
            name="ck_prediction_models_model_type",
        ),
        CheckConstraint(
            "status IN ('running', 'error', 'disabled')",
            name="ck_prediction_models_status",
        ),
        CheckConstraint(
            "api_auth_type IN ('api_key', 'bearer', 'none')",
            name="ck_prediction_models_auth_type",
        ),
    )

    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("power_stations.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'wind'"),
    )
    api_endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    api_auth_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'api_key'"),
    )
    call_frequency_cron: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'0 6,12 * * *'"),
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'disabled'"),
    )
    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_check_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_check_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_fetch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_fetch_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PowerPrediction(Base):
    """功率预测数据 - TimescaleDB hypertable，按 prediction_date 分区。"""

    __tablename__ = "power_predictions"
    __table_args__ = (
        PrimaryKeyConstraint("id", "prediction_date"),
        Index("ix_power_predictions_station_date", "station_id", "prediction_date"),
        UniqueConstraint(
            "station_id",
            "prediction_date",
            "period",
            "model_id",
            name="uq_power_predictions_station_date_period_model",
        ),
        CheckConstraint(
            "period >= 1 AND period <= 96",
            name="ck_power_predictions_period",
        ),
        CheckConstraint(
            "confidence_upper_kw >= predicted_power_kw AND predicted_power_kw >= confidence_lower_kw",
            name="ck_power_predictions_confidence",
        ),
        {"schema": "timeseries"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("power_stations.id"), nullable=False,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prediction_models.id"), nullable=False,
    )
    predicted_power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence_upper_kw: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence_lower_kw: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'api'"),
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
