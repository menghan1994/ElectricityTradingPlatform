"""种子数据脚本 — 创建示例电站和储能设备

用法：
    cd api-server
    python -m scripts.seed_stations

幂等：按 name 判断，已存在则跳过。
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.station import PowerStation
from app.models.storage import StorageDevice

STATIONS = [
    {
        "name": "广东风电一号",
        "province": "广东",
        "capacity_mw": Decimal("100.00"),
        "station_type": "wind",
        "has_storage": True,
    },
    {
        "name": "山东光伏一号",
        "province": "山东",
        "capacity_mw": Decimal("50.00"),
        "station_type": "solar",
        "has_storage": False,
    },
    {
        "name": "江苏风光互补一号",
        "province": "江苏",
        "capacity_mw": Decimal("200.00"),
        "station_type": "hybrid",
        "has_storage": True,
    },
    {
        "name": "浙江光伏一号",
        "province": "浙江",
        "capacity_mw": Decimal("80.00"),
        "station_type": "solar",
        "has_storage": False,
    },
]


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        created_stations: dict[str, PowerStation] = {}

        for station_data in STATIONS:
            result = await session.execute(
                select(PowerStation).where(PowerStation.name == station_data["name"]),
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"电站 '{station_data['name']}' 已存在，跳过。")
                created_stations[station_data["name"]] = existing
            else:
                station = PowerStation(**station_data)
                session.add(station)
                await session.flush()
                created_stations[station_data["name"]] = station
                print(f"电站 '{station_data['name']}' 创建成功。")

        # 为有储能的电站创建储能设备
        storage_configs = [
            {
                "station_name": "广东风电一号",
                "devices": [
                    {
                        "name": "广东风电一号-储能A",
                        "capacity_mwh": Decimal("50.00"),
                        "max_charge_rate_mw": Decimal("25.00"),
                        "max_discharge_rate_mw": Decimal("25.00"),
                        "soc_upper_limit": Decimal("0.9000"),
                        "soc_lower_limit": Decimal("0.1000"),
                    },
                ],
            },
            {
                "station_name": "江苏风光互补一号",
                "devices": [
                    {
                        "name": "江苏风光互补一号-储能A",
                        "capacity_mwh": Decimal("100.00"),
                        "max_charge_rate_mw": Decimal("50.00"),
                        "max_discharge_rate_mw": Decimal("50.00"),
                        "soc_upper_limit": Decimal("0.9500"),
                        "soc_lower_limit": Decimal("0.0500"),
                    },
                    {
                        "name": "江苏风光互补一号-储能B",
                        "capacity_mwh": Decimal("80.00"),
                        "max_charge_rate_mw": Decimal("40.00"),
                        "max_discharge_rate_mw": Decimal("40.00"),
                        "soc_upper_limit": Decimal("0.9000"),
                        "soc_lower_limit": Decimal("0.1000"),
                    },
                ],
            },
        ]

        for config in storage_configs:
            station = created_stations.get(config["station_name"])
            if not station:
                print(f"电站 '{config['station_name']}' 未找到，跳过储能设备创建。")
                continue

            for device_data in config["devices"]:
                # 按 station_id + name 联合查询（与 uq_storage_devices_station_name 约束一致）
                result = await session.execute(
                    select(StorageDevice).where(
                        StorageDevice.station_id == station.id,
                        StorageDevice.name == device_data["name"],
                    ),
                )
                existing_device = result.scalar_one_or_none()
                if existing_device:
                    print(f"储能设备 '{device_data['name']}' 已存在，跳过。")
                else:
                    device = StorageDevice(station_id=station.id, **device_data)
                    session.add(device)
                    print(f"储能设备 '{device_data['name']}' 创建成功。")

        await session.commit()
        print("\n种子数据创建完成。")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
