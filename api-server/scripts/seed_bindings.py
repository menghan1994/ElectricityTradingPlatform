"""种子数据脚本 — 创建示例用户-电站/设备绑定关系

用法：
    cd api-server
    python -m scripts.seed_bindings

前提：已运行 seed_admin、seed_test_users、seed_stations。
幂等：已存在的绑定会跳过（唯一约束保护）。
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.binding import UserDeviceBinding, UserStationBinding
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.models.user import User


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 查找交易员
        result = await session.execute(select(User).where(User.role == "trader"))
        traders = list(result.scalars().all())

        # 查找运维员
        result = await session.execute(select(User).where(User.role == "storage_operator"))
        operators = list(result.scalars().all())

        # 查找所有活跃电站
        result = await session.execute(
            select(PowerStation).where(PowerStation.is_active.is_(True)),
        )
        stations = list(result.scalars().all())

        # 查找所有活跃储能设备
        result = await session.execute(
            select(StorageDevice).where(StorageDevice.is_active.is_(True)),
        )
        devices = list(result.scalars().all())

        if not traders:
            print("未找到交易员用户，请先运行 seed_test_users。")
        elif not stations:
            print("未找到电站，请先运行 seed_stations。")
        else:
            # 为第一个交易员绑定前两个电站
            trader = traders[0]
            for station in stations[:2]:
                result = await session.execute(
                    select(UserStationBinding).where(
                        UserStationBinding.user_id == trader.id,
                        UserStationBinding.station_id == station.id,
                    ),
                )
                if result.scalar_one_or_none():
                    print(f"绑定 '{trader.username}' → '{station.name}' 已存在，跳过。")
                else:
                    binding = UserStationBinding(user_id=trader.id, station_id=station.id)
                    session.add(binding)
                    print(f"绑定 '{trader.username}' → '{station.name}' 创建成功。")

        if not operators:
            print("未找到储能运维员用户，请先运行 seed_test_users。")
        elif not devices:
            print("未找到储能设备，请先运行 seed_stations。")
        else:
            # 为第一个运维员绑定所有设备
            operator = operators[0]
            for device in devices:
                result = await session.execute(
                    select(UserDeviceBinding).where(
                        UserDeviceBinding.user_id == operator.id,
                        UserDeviceBinding.device_id == device.id,
                    ),
                )
                if result.scalar_one_or_none():
                    print(f"绑定 '{operator.username}' → '{device.name}' 已存在，跳过。")
                else:
                    binding = UserDeviceBinding(user_id=operator.id, device_id=device.id)
                    session.add(binding)
                    print(f"绑定 '{operator.username}' → '{device.name}' 创建成功。")

        await session.commit()
        print("\n绑定种子数据创建完成。")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
