import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class StorageDevice(Base, IdMixin, TimestampMixin):
    __tablename__ = "storage_devices"

    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("power_stations.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity_mwh: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_charge_rate_mw: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_discharge_rate_mw: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    soc_upper_limit: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default=text("0.9"),
    )
    soc_lower_limit: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default=text("0.1"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("station_id", "name", name="uq_storage_devices_station_name"),
        CheckConstraint(
            "soc_lower_limit >= 0 AND soc_upper_limit <= 1 AND soc_lower_limit < soc_upper_limit",
            name="ck_storage_devices_soc_range",
        ),
        CheckConstraint("capacity_mwh > 0", name="ck_storage_devices_capacity"),
        CheckConstraint("max_charge_rate_mw > 0", name="ck_storage_devices_charge_rate"),
        CheckConstraint("max_discharge_rate_mw > 0", name="ck_storage_devices_discharge_rate"),
    )
