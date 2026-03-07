from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import PowerPrediction, PredictionModel
from app.models.station import PowerStation
from app.repositories.base import BaseRepository


class PredictionModelRepository(BaseRepository[PredictionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(PredictionModel, session)

    async def get_by_station_id(self, station_id: UUID) -> list[PredictionModel]:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.station_id == station_id)
            .order_by(PredictionModel.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active(self) -> list[PredictionModel]:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.is_active.is_(True))
            .order_by(PredictionModel.model_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active_with_station_name(self) -> list[tuple[PredictionModel, str | None]]:
        """获取所有活跃模型及其关联电站名称。"""
        stmt = (
            select(PredictionModel, PowerStation.name)
            .outerjoin(PowerStation, PredictionModel.station_id == PowerStation.id)
            .where(PredictionModel.is_active.is_(True))
            .order_by(PredictionModel.model_name)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_station_name_by_model_id(self, model_id: UUID) -> str | None:
        """获取指定模型关联的电站名称（单次 JOIN 查询）。"""
        stmt = (
            select(PowerStation.name)
            .join(PredictionModel, PredictionModel.station_id == PowerStation.id)
            .where(PredictionModel.id == model_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        model_id: UUID,
        status: str,
    ) -> None:
        stmt = (
            update(PredictionModel)
            .where(PredictionModel.id == model_id)
            .values(status=status)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_check_result(
        self,
        model_id: UUID,
        status: str,
        check_status: str,
        error: str | None = None,
        check_at: datetime | None = None,
    ) -> None:
        values: dict = {
            "status": status,
            "last_check_status": check_status,
            "last_check_error": error,
        }
        if check_at is not None:
            values["last_check_at"] = check_at
        stmt = (
            update(PredictionModel)
            .where(PredictionModel.id == model_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_all_running(self) -> list[PredictionModel]:
        stmt = (
            select(PredictionModel)
            .where(
                PredictionModel.is_active.is_(True),
                PredictionModel.status == "running",
            )
            .order_by(PredictionModel.model_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_fetch_result(
        self,
        model_id: UUID,
        status: str,
        error: str | None = None,
        fetch_at: datetime | None = None,
    ) -> None:
        values: dict = {
            "last_fetch_status": status,
            "last_fetch_error": error,
        }
        if fetch_at is not None:
            values["last_fetch_at"] = fetch_at
        stmt = (
            update(PredictionModel)
            .where(PredictionModel.id == model_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def list_all_paginated(
        self,
        station_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PredictionModel], int]:
        page_size = min(page_size, 100)

        stmt = select(PredictionModel)
        count_stmt = select(func.count()).select_from(PredictionModel)

        if station_id is not None:
            stmt = stmt.where(PredictionModel.station_id == station_id)
            count_stmt = count_stmt.where(PredictionModel.station_id == station_id)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(PredictionModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        models = list(result.scalars().all())
        return models, total


def build_prediction_upsert_stmt(records: list[dict]):
    """构建功率预测数据的 PostgreSQL upsert 语句（供 Repository 和 Celery 任务共享）。"""
    stmt = pg_insert(PowerPrediction).values(records)
    return stmt.on_conflict_do_update(
        index_elements=["station_id", "prediction_date", "period", "model_id"],
        set_={
            "predicted_power_kw": stmt.excluded.predicted_power_kw,
            "confidence_upper_kw": stmt.excluded.confidence_upper_kw,
            "confidence_lower_kw": stmt.excluded.confidence_lower_kw,
            "source": stmt.excluded.source,
            "fetched_at": stmt.excluded.fetched_at,
        },
    )


class PowerPredictionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        stmt = build_prediction_upsert_stmt(records)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_by_station_date_model(
        self,
        station_id: UUID,
        prediction_date: date,
        model_id: UUID | None = None,
    ) -> list[PowerPrediction]:
        stmt = select(PowerPrediction).where(
            PowerPrediction.station_id == station_id,
            PowerPrediction.prediction_date == prediction_date,
        )
        if model_id is not None:
            stmt = stmt.where(PowerPrediction.model_id == model_id)
        stmt = stmt.order_by(PowerPrediction.period)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_station(
        self, station_id: UUID,
    ) -> PowerPrediction | None:
        stmt = (
            select(PowerPrediction)
            .where(PowerPrediction.station_id == station_id)
            .order_by(
                PowerPrediction.prediction_date.desc(),
                PowerPrediction.period.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
