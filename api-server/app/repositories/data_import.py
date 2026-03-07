from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_import import (
    DataImportJob,
    ImportAnomaly,
    StationOutputRecord,
    StorageOperationRecord,
    TradingRecord,
)
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
        import_type_filter: str | None = None,
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

        if import_type_filter:
            stmt = stmt.where(DataImportJob.import_type == import_type_filter)
            count_stmt = count_stmt.where(DataImportJob.import_type == import_type_filter)

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
        completed_at: datetime | None = None,
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

    async def upsert_record(self, record: dict) -> int:
        """插入或更新单条交易记录（用于异常修正写入）。"""
        stmt = pg_insert(TradingRecord).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=["station_id", "trading_date", "period"],
            set_={
                "clearing_price": stmt.excluded.clearing_price,
                "import_job_id": stmt.excluded.import_job_id,
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_by_keys(
        self,
        station_id: UUID,
        trading_date: date,
        period: int,
    ) -> int:
        """按唯一键删除交易记录（用于 duplicate 类型异常处理）。"""
        stmt = (
            delete(TradingRecord)
            .where(
                TradingRecord.station_id == station_id,
                TradingRecord.trading_date == trading_date,
                TradingRecord.period == period,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount


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

    async def get_by_ids(self, anomaly_ids: list[UUID]) -> list[ImportAnomaly]:
        """批量按 ID 查询异常记录（单次 SELECT IN 查询）。"""
        if not anomaly_ids:
            return []
        stmt = select(ImportAnomaly).where(ImportAnomaly.id.in_(anomaly_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_for_update(self, anomaly_id: UUID) -> ImportAnomaly | None:
        stmt = (
            select(ImportAnomaly)
            .where(ImportAnomaly.id == anomaly_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_anomalies(
        self,
        page: int = 1,
        page_size: int = 20,
        anomaly_type_filter: str | None = None,
        status_filter: str | None = None,
        import_job_id_filter: UUID | None = None,
    ) -> tuple[list[ImportAnomaly], int]:
        page_size = min(page_size, 100)

        stmt = select(ImportAnomaly)
        count_stmt = select(func.count()).select_from(ImportAnomaly)

        if anomaly_type_filter:
            stmt = stmt.where(ImportAnomaly.anomaly_type == anomaly_type_filter)
            count_stmt = count_stmt.where(ImportAnomaly.anomaly_type == anomaly_type_filter)

        if status_filter:
            stmt = stmt.where(ImportAnomaly.status == status_filter)
            count_stmt = count_stmt.where(ImportAnomaly.status == status_filter)

        if import_job_id_filter:
            stmt = stmt.where(ImportAnomaly.import_job_id == import_job_id_filter)
            count_stmt = count_stmt.where(ImportAnomaly.import_job_id == import_job_id_filter)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(ImportAnomaly.created_at.desc(), ImportAnomaly.row_number)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        anomalies = list(result.scalars().all())

        return anomalies, total

    async def update_anomaly_status(
        self,
        anomaly_id: UUID,
        new_status: str,
    ) -> None:
        anomaly = await self.get_by_id(anomaly_id)
        if anomaly:
            anomaly.status = new_status
            await self.session.flush()
            await self.session.refresh(anomaly)

    async def bulk_update_status(
        self,
        anomaly_ids: list[UUID],
        new_status: str,
    ) -> int:
        if not anomaly_ids:
            return 0
        stmt = (
            update(ImportAnomaly)
            .where(
                ImportAnomaly.id.in_(anomaly_ids),
                ImportAnomaly.status == "pending",
            )
            .values(status=new_status)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def update_anomaly_value(
        self,
        anomaly_id: UUID,
        corrected_value: str,
        new_status: str,
    ) -> None:
        anomaly = await self.get_by_id(anomaly_id)
        if anomaly:
            anomaly.raw_value = corrected_value
            anomaly.status = new_status
            await self.session.flush()

    async def get_summary_all(
        self,
        import_job_id_filter: UUID | None = None,
        status_filter: str | None = None,
    ) -> list[dict]:
        stmt = (
            select(
                ImportAnomaly.anomaly_type,
                func.count().label("count"),
            )
            .group_by(ImportAnomaly.anomaly_type)
        )

        if import_job_id_filter:
            stmt = stmt.where(ImportAnomaly.import_job_id == import_job_id_filter)

        if status_filter:
            stmt = stmt.where(ImportAnomaly.status == status_filter)

        result = await self.session.execute(stmt)
        return [{"anomaly_type": row.anomaly_type, "count": row.count} for row in result.all()]


class StationOutputRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, records: list[dict]) -> int:
        if not records:
            return 0
        stmt = pg_insert(StationOutputRecord).values(records)
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
            select(StationOutputRecord.trading_date, StationOutputRecord.period)
            .where(
                StationOutputRecord.station_id == station_id,
                StationOutputRecord.trading_date.in_(trading_dates),
            )
        )
        result = await self.session.execute(stmt)
        return {(row.trading_date, row.period) for row in result.all()}

    async def list_by_job(
        self,
        import_job_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StationOutputRecord], int]:
        page_size = min(page_size, 100)
        count_stmt = (
            select(func.count())
            .select_from(StationOutputRecord)
            .where(StationOutputRecord.import_job_id == import_job_id)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(StationOutputRecord)
            .where(StationOutputRecord.import_job_id == import_job_id)
            .order_by(StationOutputRecord.trading_date, StationOutputRecord.period)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def upsert_record(self, record: dict) -> int:
        stmt = pg_insert(StationOutputRecord).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=["station_id", "trading_date", "period"],
            set_={
                "actual_output_kw": stmt.excluded.actual_output_kw,
                "import_job_id": stmt.excluded.import_job_id,
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount


class StorageOperationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert(self, records: list[dict]) -> int:
        if not records:
            return 0
        stmt = pg_insert(StorageOperationRecord).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["device_id", "trading_date", "period"],
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def check_duplicates(
        self,
        device_id: UUID,
        trading_dates: list[date],
    ) -> set[tuple[date, int]]:
        if not trading_dates:
            return set()
        stmt = (
            select(StorageOperationRecord.trading_date, StorageOperationRecord.period)
            .where(
                StorageOperationRecord.device_id == device_id,
                StorageOperationRecord.trading_date.in_(trading_dates),
            )
        )
        result = await self.session.execute(stmt)
        return {(row.trading_date, row.period) for row in result.all()}

    async def list_by_job(
        self,
        import_job_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StorageOperationRecord], int]:
        page_size = min(page_size, 100)
        count_stmt = (
            select(func.count())
            .select_from(StorageOperationRecord)
            .where(StorageOperationRecord.import_job_id == import_job_id)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(StorageOperationRecord)
            .where(StorageOperationRecord.import_job_id == import_job_id)
            .order_by(StorageOperationRecord.trading_date, StorageOperationRecord.period)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def upsert_record(self, record: dict) -> int:
        stmt = pg_insert(StorageOperationRecord).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=["device_id", "trading_date", "period"],
            set_={
                "soc": stmt.excluded.soc,
                "charge_power_kw": stmt.excluded.charge_power_kw,
                "discharge_power_kw": stmt.excluded.discharge_power_kw,
                "cycle_count": stmt.excluded.cycle_count,
                "import_job_id": stmt.excluded.import_job_id,
            },
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_latest_soc(self, device_id: UUID) -> tuple[date, int, float] | None:
        """获取设备最新时段的 SOC 值。"""
        stmt = (
            select(
                StorageOperationRecord.trading_date,
                StorageOperationRecord.period,
                StorageOperationRecord.soc,
            )
            .where(StorageOperationRecord.device_id == device_id)
            .order_by(
                StorageOperationRecord.trading_date.desc(),
                StorageOperationRecord.period.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row:
            return row.trading_date, row.period, float(row.soc)
        return None
