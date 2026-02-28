"""create power_stations, storage_devices, user_station_bindings, user_device_bindings tables

电站基础表、储能设备表、用户-电站绑定关联表、用户-设备绑定关联表。
支撑交易员-电站绑定和运维员-设备绑定功能。

Revision ID: 005_stations_devices_bindings
Revises: 004_drop_audit_fk
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "005_stations_devices_bindings"
down_revision = "004_drop_audit_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # power_stations 表
    op.create_table(
        "power_stations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("province", sa.String(50), nullable=False),
        sa.Column("capacity_mw", sa.Numeric(10, 2), nullable=False),
        sa.Column("station_type", sa.String(20), nullable=False),
        sa.Column("has_storage", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_power_stations_province", "power_stations", ["province"])
    op.create_check_constraint(
        "ck_power_stations_station_type", "power_stations",
        "station_type IN ('wind', 'solar', 'hybrid')",
    )
    op.create_check_constraint(
        "ck_power_stations_capacity", "power_stations",
        "capacity_mw > 0",
    )

    # storage_devices 表
    op.create_table(
        "storage_devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("station_id", UUID(as_uuid=True), sa.ForeignKey("power_stations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capacity_mwh", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_charge_rate_mw", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_discharge_rate_mw", sa.Numeric(10, 2), nullable=False),
        sa.Column("soc_upper_limit", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.9")),
        sa.Column("soc_lower_limit", sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.1")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # 同一电站下设备名称唯一（与 ORM 模型 storage.py 一致）
    op.create_unique_constraint(
        "uq_storage_devices_station_name", "storage_devices", ["station_id", "name"],
    )
    op.create_check_constraint(
        "ck_storage_devices_soc_range", "storage_devices",
        "soc_lower_limit >= 0 AND soc_upper_limit <= 1 AND soc_lower_limit < soc_upper_limit",
    )
    op.create_check_constraint(
        "ck_storage_devices_capacity", "storage_devices",
        "capacity_mwh > 0",
    )
    op.create_check_constraint(
        "ck_storage_devices_charge_rate", "storage_devices",
        "max_charge_rate_mw > 0",
    )
    op.create_check_constraint(
        "ck_storage_devices_discharge_rate", "storage_devices",
        "max_discharge_rate_mw > 0",
    )

    # user_station_bindings 关联表
    op.create_table(
        "user_station_bindings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("station_id", UUID(as_uuid=True), sa.ForeignKey("power_stations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "station_id", name="uq_user_station_bindings_user_station"),
    )
    op.create_index("ix_user_station_bindings_station_id", "user_station_bindings", ["station_id"])

    # user_device_bindings 关联表
    op.create_table(
        "user_device_bindings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("storage_devices.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "device_id", name="uq_user_device_bindings_user_device"),
    )
    op.create_index("ix_user_device_bindings_device_id", "user_device_bindings", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_user_device_bindings_device_id", "user_device_bindings")
    op.drop_table("user_device_bindings")
    op.drop_index("ix_user_station_bindings_station_id", "user_station_bindings")
    op.drop_table("user_station_bindings")
    op.drop_table("storage_devices")
    op.drop_index("ix_power_stations_province", "power_stations")
    op.drop_table("power_stations")
