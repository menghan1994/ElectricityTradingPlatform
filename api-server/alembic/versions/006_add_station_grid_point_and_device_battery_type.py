"""add grid_connection_point to power_stations and battery_type to storage_devices

PowerStation 表添加并网点字段，StorageDevice 表添加电池类型字段（含 CHECK 约束）。
支撑电站配置向导功能（Story 2.1）。

Revision ID: 006_station_grid_device_battery
Revises: 005_stations_devices_bindings
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from alembic import op

revision = "006_station_grid_device_battery"
down_revision = "005_stations_devices_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PowerStation: 添加并网点字段（可空）
    op.add_column(
        "power_stations",
        sa.Column("grid_connection_point", sa.String(200), nullable=True),
    )

    # StorageDevice: 添加电池类型字段（可空）+ CHECK 约束
    op.add_column(
        "storage_devices",
        sa.Column("battery_type", sa.String(50), nullable=True),
    )
    op.create_check_constraint(
        "ck_storage_devices_battery_type",
        "storage_devices",
        "battery_type IS NULL OR battery_type IN ('lfp', 'nmc', 'lto', 'other')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_storage_devices_battery_type", "storage_devices", type_="check")
    op.drop_column("storage_devices", "battery_type")
    op.drop_column("power_stations", "grid_connection_point")
