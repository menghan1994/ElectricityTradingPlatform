from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class PowerStation(Base, IdMixin, TimestampMixin):
    __tablename__ = "power_stations"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_mw: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    station_type: Mapped[str] = mapped_column(String(20), nullable=False)
    grid_connection_point: Mapped[str | None] = mapped_column(String(200), nullable=True)
    has_storage: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        Index("ix_power_stations_province", "province"),
        CheckConstraint(
            "station_type IN ('wind', 'solar', 'hybrid')",
            name="ck_power_stations_station_type",
        ),
        CheckConstraint("capacity_mw > 0", name="ck_power_stations_capacity"),
    )
