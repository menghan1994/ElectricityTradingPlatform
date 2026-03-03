from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_import import DataImportJob, ImportAnomaly, TradingRecord
from app.repositories.base import BaseRepository


class DataImportJobRepository(BaseRepository[DataImportJob]):
    def __init__(self, session: AsyncSession):
        super().__init__(DataImportJob, session)

    async def get_by_id_for_update(self, job_id: UUID) -> DataImportJob | None:
        stmt = (
            select(DataImportJob)
            .where(DataImportJob.id == job_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_station(
        self,
        station_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DataImportJob], int]:
        page_size = min(page_size, 100)

        count_stmt = (
            select(func.count())
            .select_from(DataImportJob)
            .where(DataImportJob.station_id == station_id)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(DataImportJob)
            .where(DataImportJob.station_id == station_id)
            .order_by(DataImportJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_all_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        station_id: UUID | None = None,
    ) -> tuple[list[DataImportJob], int]:
        page_size = min(page_size, 100)

        stmt = select(DataImportJob)
        count_stmt = select(func.count()).select_from(DataImportJob)

        if status_filter:
            stmt = stmt.where(DataImportJob.status == status_filter)
            count_stmt = count_stmt.where(DataImportJob.status == status_filter)

        if station_id:
            stmt = stmt.where(DataImportJob.station_id == station_id)
            count_stmt = count_stmt.where(DataImportJob.station_id == station_id)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(DataImportJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        return jobs, total

    async def update_progress(
        self,
        job_id: UUID,
        processed_records: int,
        success_records: int,
        failed_records: int,
        last_processed_row: int,
    ) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.processed_records = processed_records
            job.success_records = success_records
            job.failed_records = failed_records
            job.last_processed_row = last_processed_row
            await self.session.flush()

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        error_message: str | None = None,
        completed_at: object = None,
    ) -> None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = status
            if error_message is not None:
                job.error_message = error_message
            if completed_at is not None:
                job.completed_at = completed_at
            await self.session.flush()

    async def has_processing_job(self, station_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(DataImportJob)
            .where(
                DataImportJob.station_id == station_id,
                DataImportJob.status.in_(["pending", "processing"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def list_expired_jobs(
        self,
        statuses: list[str],
        before: datetime,
    ) -> list[DataImportJob]:
        """查询指定状态且更新时间早于 cutoff 的任务。"""
        stmt = (
            select(DataImportJob)
            .where(
                DataImportJob.status.in_(statuses),
                DataImportJob.updated_at < before,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TradingRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, records: list[dict]) -> int:
        if not records:
            return 0
        stmt = pg_insert(TradingRecord).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["station_id", "trading_date", "period"],
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def check_duplicates(
        self,
        station_id: UUID,
        trading_dates: list[date],
    ) -> set[tuple[date, int]]:
        if not trading_dates:
            return set()
        stmt = (
            select(TradingRecord.trading_date, TradingRecord.period)
            .where(
                TradingRecord.station_id == station_id,
                TradingRecord.trading_date.in_(trading_dates),
            )
        )
        result = await self.session.execute(stmt)
        return {(row.trading_date, row.period) for row in result.all()}

    async def count_by_station(self, station_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(TradingRecord)
            .where(TradingRecord.station_id == station_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_date_range(self, station_id: UUID) -> tuple[date | None, date | None]:
        stmt = select(
            func.min(TradingRecord.trading_date),
            func.max(TradingRecord.trading_date),
        ).where(TradingRecord.station_id == station_id)
        result = await self.session.execute(stmt)
        row = result.one()
        return row[0], row[1]


class ImportAnomalyRepository(BaseRepository[ImportAnomaly]):
    def __init__(self, session: AsyncSession):
        super().__init__(ImportAnomaly, session)

    async def bulk_create(self, anomalies: list[dict]) -> None:
        if not anomalies:
            return
        stmt = insert(ImportAnomaly).values(anomalies)
        await self.session.execute(stmt)

    async def list_by_job(
        self,
        job_id: UUID,
        page: int = 1,
        page_size: int = 20,
        anomaly_type_filter: str | None = None,
    ) -> tuple[list[ImportAnomaly], int]:
        page_size = min(page_size, 100)

        stmt = select(ImportAnomaly).where(ImportAnomaly.import_job_id == job_id)
        count_stmt = (
            select(func.count())
            .select_from(ImportAnomaly)
            .where(ImportAnomaly.import_job_id == job_id)
        )

        if anomaly_type_filter:
            stmt = stmt.where(ImportAnomaly.anomaly_type == anomaly_type_filter)
            count_stmt = count_stmt.where(ImportAnomaly.anomaly_type == anomaly_type_filter)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(ImportAnomaly.row_number)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        anomalies = list(result.scalars().all())

        return anomalies, total

    async def get_summary_by_job(self, job_id: UUID) -> list[dict]:
        stmt = (
            select(
                ImportAnomaly.anomaly_type,
                func.count().label("count"),
            )
            .where(ImportAnomaly.import_job_id == job_id)
            .group_by(ImportAnomaly.anomaly_type)
        )
        result = await self.session.execute(stmt)
        return [{"anomaly_type": row.anomaly_type, "count": row.count} for row in result.all()]
