"""Mock 省级电力交易中心 API — 用于开发和测试市场数据自动获取功能。

启动方式:
    uvicorn main:app --host 0.0.0.0 --port 8080
    或通过 docker compose -f docker-compose.yml -f docker-compose.dev.yml up mock-market-api

环境变量:
    MOCK_FAILURE_RATE  — 模拟失败概率 (0.0~1.0, 默认 0)
    MOCK_DELAY_SECONDS — 模拟响应延迟秒数 (默认 0)
    MOCK_API_KEY       — 如设置，则要求 X-API-Key 或 Bearer 认证
"""

import asyncio
import hashlib
import math
import os
import random
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request

app = FastAPI(title="Mock 省级电力交易中心 API", version="1.0.0")

FAILURE_RATE = float(os.environ.get("MOCK_FAILURE_RATE", "0"))
DELAY_SECONDS = float(os.environ.get("MOCK_DELAY_SECONDS", "0"))
REQUIRED_API_KEY = os.environ.get("MOCK_API_KEY", "")

PERIODS_PER_DAY = 96

# 时段价格基准 (元/MWh) — 模拟日内价格曲线
# 谷段(23:00-07:00, 时段69-96+1-28): 低价, 平段: 中价, 峰段(10:00-12:00, 17:00-21:00): 高价
VALLEY_PERIODS = set(range(69, 97)) | set(range(1, 29))  # 23:00-07:00
PEAK_PERIODS = set(range(37, 49)) | set(range(65, 85))  # 10:00-12:00, 17:00-21:00


def _generate_price(period: int, seed: str) -> float:
    """基于时段和种子生成合理的出清价格。

    使用种子确保同一 trading_date + period 组合总是返回相同价格，
    便于调试和验证。
    """
    rng = random.Random(hashlib.md5(f"{seed}:{period}".encode()).hexdigest())

    if period in VALLEY_PERIODS:
        base = rng.uniform(180, 260)
    elif period in PEAK_PERIODS:
        base = rng.uniform(360, 480)
    else:
        base = rng.uniform(280, 360)

    # 加入小幅随机波动
    noise = rng.gauss(0, 5)
    return round(base + noise, 2)


def _check_auth(request: Request) -> None:
    """可选的认证校验。"""
    if not REQUIRED_API_KEY:
        return

    api_key = request.headers.get("X-API-Key", "")
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if api_key != REQUIRED_API_KEY and bearer_token != REQUIRED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/market-data")
async def get_market_data(
    request: Request,
    trading_date: date = Query(..., description="交易日期 YYYY-MM-DD"),
):
    """返回指定交易日的 96 时段出清价格数据。

    响应格式与 GenericMarketDataAdapter 期望的标准 JSON API 格式一致。
    """
    _check_auth(request)

    # 模拟延迟
    if DELAY_SECONDS > 0:
        await asyncio.sleep(DELAY_SECONDS)

    # 模拟随机失败
    if FAILURE_RATE > 0 and random.random() < FAILURE_RATE:
        raise HTTPException(status_code=503, detail="模拟: 服务暂时不可用")

    seed = trading_date.isoformat()
    data = [
        {
            "period": period,
            "clearing_price": _generate_price(period, seed),
        }
        for period in range(1, PERIODS_PER_DAY + 1)
    ]

    return {"data": data}


@app.get("/predictions")
async def get_predictions(
    request: Request,
    station_id: str = Query(..., description="电站 ID"),
    prediction_date: date = Query(..., description="预测日期 YYYY-MM-DD"),
):
    """返回指定电站指定日期的96时段功率预测数据。

    支持 wind/solar 两种模式（基于 station_id 哈希自动区分）。
    响应格式兼容 GenericPredictionAdapter：裸数组或 {"data": [...]} 信封。
    """
    _check_auth(request)

    if DELAY_SECONDS > 0:
        await asyncio.sleep(DELAY_SECONDS)

    if FAILURE_RATE > 0 and random.random() < FAILURE_RATE:
        raise HTTPException(status_code=503, detail="模拟: 服务暂时不可用")

    seed = f"{station_id}:{prediction_date.isoformat()}"
    # 根据 station_id 哈希决定 wind/solar 模式
    is_solar = int(hashlib.md5(station_id.encode()).hexdigest(), 16) % 2 == 0

    data = []
    for period in range(1, PERIODS_PER_DAY + 1):
        rng = random.Random(hashlib.md5(f"{seed}:{period}".encode()).hexdigest())

        if is_solar:
            # 光伏: 白天高夜间低 (0-5000kW)
            # 时段1=00:00, 每时段15分钟, 白天大约时段25-68 (06:00-17:00)
            hour = (period - 1) * 15 / 60
            if 6 <= hour <= 17:
                # 正弦曲线模拟日照
                solar_factor = math.sin(math.pi * (hour - 6) / 11)
                base = rng.uniform(3000, 5000) * solar_factor
            else:
                base = 0.0
        else:
            # 风电: 500-3000kW 有波动
            base = rng.uniform(500, 3000)

        noise = rng.gauss(0, base * 0.05) if base > 0 else 0
        predicted = round(max(0, base + noise), 2)
        # 置信区间: ±10%-20%
        margin = rng.uniform(0.10, 0.20)
        upper = round(predicted * (1 + margin), 2)
        lower = round(predicted * (1 - margin), 2)
        lower = max(0, lower)

        data.append({
            "period": period,
            "predicted_power_kw": predicted,
            "confidence_upper_kw": upper,
            "confidence_lower_kw": lower,
        })

    return {"data": data}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-market-api"}
