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


class MarketClearingPrice(Base):
    """省级市场出清价格 - TimescaleDB hypertable，按 trading_date 分区。"""

    __tablename__ = "market_clearing_prices"
    __table_args__ = (
        PrimaryKeyConstraint("id", "trading_date"),
        Index("ix_market_clearing_prices_province_date", "province", "trading_date"),
        UniqueConstraint(
            "province",
            "trading_date",
            "period",
            name="uq_market_clearing_prices_province_date_period",
        ),
        CheckConstraint(
            "period >= 1 AND period <= 96",
            name="ck_market_clearing_prices_period",
        ),
        CheckConstraint(
            "source IN ('api', 'manual_import')",
            name="ck_market_clearing_prices_source",
        ),
        {"schema": "timeseries"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    clearing_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'api'"),
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_import_jobs.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )


class MarketDataSource(Base, IdMixin, TimestampMixin):
    """市场数据源配置 - 省级电力交易中心 API 接入参数。"""

    __tablename__ = "market_data_sources"
    __table_args__ = (
        CheckConstraint(
            "api_auth_type IN ('api_key', 'bearer', 'none')",
            name="ck_market_data_sources_auth_type",
        ),
        CheckConstraint(
            "last_fetch_status IN ('pending', 'success', 'failed')",
            name="ck_market_data_sources_fetch_status",
        ),
        CheckConstraint(
            "cache_ttl_seconds > 0",
            name="ck_market_data_sources_cache_ttl",
        ),
    )

    province: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    api_auth_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'api_key'"),
    )
    fetch_schedule: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'0 7,12,17 * * *'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )
    last_fetch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_fetch_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'"),
    )
    last_fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_ttl_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("3600"),
    )
