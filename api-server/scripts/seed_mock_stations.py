"""种子数据脚本 — 批量创建模拟电站和储能设备

用法：
    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        exec api-server python -m scripts.seed_mock_stations

幂等：按 name 判断，已存在则跳过。
"""

import asyncio
import random
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.station import PowerStation
from app.models.storage import StorageDevice

# ---------------------------------------------------------------------------
# 配置区
# ---------------------------------------------------------------------------

# C2: 使用拼音省份名称（与后端 Province Literal 一致）
PROVINCES = [
    "guangdong", "shandong", "jiangsu", "zhejiang", "hebei", "neimenggu",
    "gansu", "xinjiang", "yunnan", "hubei", "fujian", "liaoning",
    "anhui", "henan", "sichuan", "qinghai", "ningxia", "jilin",
]

# 拼音 → 中文映射（用于生成可读的电站名称）
PROVINCE_LABELS = {
    "guangdong": "广东", "shandong": "山东", "jiangsu": "江苏",
    "zhejiang": "浙江", "hebei": "河北", "neimenggu": "内蒙古",
    "gansu": "甘肃", "xinjiang": "新疆", "yunnan": "云南",
    "hubei": "湖北", "fujian": "福建", "liaoning": "辽宁",
    "anhui": "安徽", "henan": "河南", "sichuan": "四川",
    "qinghai": "青海", "ningxia": "宁夏", "jilin": "吉林",
}

STATION_TYPES = ["wind", "solar", "hybrid"]
TYPE_LABELS = {"wind": "风电", "solar": "光伏", "hybrid": "风光互补"}

BATTERY_TYPES = ["lfp", "nmc", "lto"]

GRID_POINTS = [
    "220kV 变电站", "110kV 变电站", "500kV 变电站", "330kV 变电站",
]

# 每种类型的容量范围 (MW)
CAPACITY_RANGES = {
    "wind": (50, 300),
    "solar": (30, 200),
    "hybrid": (100, 500),
}

random.seed(42)  # 固定种子，保证可重复


def _generate_stations(count: int = 30) -> list[dict]:
    """生成模拟电站数据列表。"""
    stations = []
    # 记录每个省+类型的计数器，用于命名
    counters: dict[str, int] = {}

    for _ in range(count):
        province = random.choice(PROVINCES)
        stype = random.choice(STATION_TYPES)
        key = f"{province}_{stype}"
        counters[key] = counters.get(key, 0) + 1
        idx = counters[key]

        province_cn = PROVINCE_LABELS[province]
        label = TYPE_LABELS[stype]
        cap_min, cap_max = CAPACITY_RANGES[stype]
        capacity = Decimal(str(random.randint(cap_min, cap_max)))

        has_storage = stype == "hybrid" or random.random() < 0.4

        grid_point = f"{province_cn}{random.choice(GRID_POINTS)}" if random.random() < 0.7 else None

        stations.append({
            "name": f"{province_cn}{label}{idx:02d}号",
            "province": province,
            "capacity_mw": capacity,
            "station_type": stype,
            "grid_connection_point": grid_point,
            "has_storage": has_storage,
        })

    return stations


def _generate_devices(station_name: str, capacity_mw: Decimal) -> list[dict]:
    """为一座电站生成 1~2 台储能设备。"""
    device_count = random.choice([1, 1, 2])  # 2/3 概率 1 台，1/3 概率 2 台
    devices = []
    for i in range(device_count):
        suffix = chr(ord("A") + i)
        # 储能容量一般为电站容量的 20%~60%
        ratio = Decimal(str(round(random.uniform(0.2, 0.6), 2)))
        cap_mwh = (capacity_mw * ratio).quantize(Decimal("0.01"))
        # 充放电功率为储能容量的 40%~60%
        rate_ratio = Decimal(str(round(random.uniform(0.4, 0.6), 2)))
        rate = (cap_mwh * rate_ratio).quantize(Decimal("0.01"))

        soc_lower = Decimal(str(round(random.uniform(0.05, 0.15), 4)))
        soc_upper = Decimal(str(round(random.uniform(0.85, 0.95), 4)))

        devices.append({
            "name": f"{station_name}-储能{suffix}",
            "capacity_mwh": cap_mwh,
            "max_charge_rate_mw": rate,
            "max_discharge_rate_mw": rate,
            "soc_upper_limit": soc_upper,
            "soc_lower_limit": soc_lower,
            "battery_type": random.choice(BATTERY_TYPES),
        })

    return devices


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stations_data = _generate_stations(30)

    async with session_factory() as session:
        created = 0
        skipped = 0
        devices_created = 0

        for sdata in stations_data:
            result = await session.execute(
                select(PowerStation).where(PowerStation.name == sdata["name"]),
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  跳过  {sdata['name']}（已存在）")
                skipped += 1
                station = existing
            else:
                station = PowerStation(**sdata)
                session.add(station)
                await session.flush()
                print(f"  创建  {sdata['name']}  {sdata['station_type']}  {sdata['capacity_mw']}MW")
                created += 1

            # 创建储能设备
            if sdata["has_storage"]:
                devices = _generate_devices(sdata["name"], sdata["capacity_mw"])
                for ddata in devices:
                    result = await session.execute(
                        select(StorageDevice).where(
                            StorageDevice.station_id == station.id,
                            StorageDevice.name == ddata["name"],
                        ),
                    )
                    if result.scalar_one_or_none():
                        print(f"    跳过  {ddata['name']}（已存在）")
                    else:
                        device = StorageDevice(station_id=station.id, **ddata)
                        session.add(device)
                        devices_created += 1
                        print(f"    创建  {ddata['name']}  {ddata['capacity_mwh']}MWh  {ddata['battery_type']}")

        await session.commit()
        print(f"\n完成: 电站 {created} 个新建 / {skipped} 个跳过，储能设备 {devices_created} 个新建。")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
