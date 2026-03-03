import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class DataImportJob(Base, IdMixin, TimestampMixin):
    __tablename__ = "data_import_jobs"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("power_stations.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
    )
    total_records: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    processed_records: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    success_records: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    failed_records: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    data_completeness: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default=text("0"),
    )
    last_processed_row: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    imported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )

    __table_args__ = (
        Index("ix_data_import_jobs_station", "station_id"),
        Index("ix_data_import_jobs_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_data_import_jobs_status",
        ),
    )


class TradingRecord(Base):
    """TimescaleDB 超表要求分区列 trading_date 必须包含在主键中。"""

    __tablename__ = "trading_records"
    __table_args__ = (
        PrimaryKeyConstraint("id", "trading_date"),
        Index("ix_trading_records_station_date", "station_id", "trading_date"),
        UniqueConstraint(
            "station_id", "trading_date", "period",
            name="uq_trading_records_station_date_period",
        ),
        CheckConstraint("period >= 1 AND period <= 96", name="ck_trading_records_period"),
        {"schema": "timeseries"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("power_stations.id"), nullable=False,
    )
    clearing_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_import_jobs.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


class ImportAnomaly(Base, IdMixin, TimestampMixin):
    __tablename__ = "import_anomalies"

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_import_jobs.id"), nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(20), nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
    )

    __table_args__ = (
        Index("ix_import_anomalies_job_id", "import_job_id"),
        Index("ix_import_anomalies_type", "anomaly_type"),
        CheckConstraint(
            "anomaly_type IN ('missing', 'format_error', 'out_of_range', 'duplicate')",
            name="ck_import_anomalies_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed_normal', 'corrected', 'deleted')",
            name="ck_import_anomalies_status",
        ),
    )
