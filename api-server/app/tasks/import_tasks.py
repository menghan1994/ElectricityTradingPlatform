import csv
import io
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import structlog

from app.core.config import settings
from app.core.database import get_sync_session_factory
from app.models.audit import AuditLog
from app.models.data_import import DataImportJob, ImportAnomaly, TradingRecord
from app.models.market_rule import ProvinceMarketRule
from app.models.station import PowerStation
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()

BATCH_SIZE = 1000

# 列头映射：支持中英文
COLUMN_MAPPING = {
    "交易日期": "trading_date",
    "时段": "period",
    "出清价格": "clearing_price",
    "trading_date": "trading_date",
    "period": "period",
    "clearing_price": "clearing_price",
}


def _parse_date(raw: str) -> date | None:
    """尝试多种日期格式解析。"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_period(raw: str) -> int | None:
    try:
        val = int(raw.strip())
        if 1 <= val <= 96:
            return val
        return None
    except (ValueError, TypeError):
        return None


def _parse_price(raw: str) -> Decimal | None:
    try:
        val = Decimal(raw.strip())
        if val.is_nan() or val.is_infinite():
            return None
        return val
    except (InvalidOperation, ValueError, TypeError):
        return None


def _detect_csv_encoding(file_path: Path) -> str:
    """检测 CSV 文件编码，先尝试 UTF-8，再尝试 GBK。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            with open(file_path, encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def _read_csv_rows(file_path: Path):
    """生成器：逐行读取 CSV 文件。"""
    encoding = _detect_csv_encoding(file_path)
    with open(file_path, encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            yield row


def _read_xlsx_rows(file_path: Path):
    """生成器：逐行读取 Excel 文件（read_only 模式）。"""
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            yield [str(cell) if cell is not None else "" for cell in row]
    finally:
        wb.close()


def _map_columns(header_row: list[str]) -> dict[int, str] | None:
    """将列头映射为标准字段名，返回 {列索引: 字段名}。"""
    col_map: dict[int, str] = {}
    required_fields = {"trading_date", "period", "clearing_price"}
    found_fields: set[str] = set()

    for i, col in enumerate(header_row):
        cleaned = col.strip().lower()
        # 先尝试原始值（大小写不敏感）
        for key, field in COLUMN_MAPPING.items():
            if cleaned == key.lower():
                col_map[i] = field
                found_fields.add(field)
                break

    if not required_fields.issubset(found_fields):
        return None
    return col_map


@celery_app.task(bind=True, max_retries=0)
def process_trading_data_import(self, job_id: str, resume_from_row: int = 0):
    """后台处理交易数据导入。"""
    SyncSessionLocal = get_sync_session_factory()
    session = SyncSessionLocal()
    try:
        _execute_import(session, self, job_id, resume_from_row)
    except Exception as e:
        session.rollback()
        # 更新状态为 failed
        try:
            job = session.get(DataImportJob, uuid.UUID(job_id))
            if job:
                job.status = "failed"
                job.error_message = str(e)[:2000]
                session.commit()
        except Exception:
            session.rollback()
        logger.error("import_task_failed", job_id=job_id, error=str(e))
        raise
    finally:
        session.close()


def _execute_import(session, task, job_id: str, resume_from_row: int):
    """核心导入逻辑。"""
    job_uuid = uuid.UUID(job_id)
    job = session.get(DataImportJob, job_uuid)
    if not job:
        raise ValueError(f"Import job {job_id} not found")

    # 更新状态为 processing
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.celery_task_id = task.request.id
    session.commit()

    # 获取电站信息和省份市场规则
    station = session.get(PowerStation, job.station_id)
    if not station:
        raise ValueError(f"Station {job.station_id} not found")

    from sqlalchemy import select as sa_select

    market_rule_stmt = sa_select(ProvinceMarketRule).where(
        ProvinceMarketRule.province == station.province,
        ProvinceMarketRule.is_active.is_(True),
    )
    market_rule = session.execute(market_rule_stmt).scalar_one_or_none()

    price_cap_upper = Decimal(str(market_rule.price_cap_upper)) if market_rule else None
    price_cap_lower = Decimal(str(market_rule.price_cap_lower)) if market_rule else None

    # 打开文件
    file_path = Path(settings.DATA_IMPORT_DIR) / job.file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Import file not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        rows = _read_csv_rows(file_path)
    elif suffix == ".xlsx":
        rows = _read_xlsx_rows(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    # 读取并验证列头
    header_row = next(rows, None)
    if header_row is None:
        raise ValueError("文件为空，无法读取列头")

    col_map = _map_columns(header_row)
    if col_map is None:
        raise ValueError(
            "列头映射失败：需要包含 trading_date/交易日期、period/时段、clearing_price/出清价格"
        )

    # 逐批处理
    writer = SyncBatchWriter(session)
    row_number = 0
    total_records = 0
    success_records = job.success_records if resume_from_row > 0 else 0
    failed_records = job.failed_records if resume_from_row > 0 else 0
    processed_records = job.processed_records if resume_from_row > 0 else 0

    batch_records: list[dict] = []
    batch_anomalies: list[dict] = []
    all_trading_dates: set[date] = set()

    for row in rows:
        row_number += 1
        total_records += 1

        # 断点续传：跳过已处理行
        if row_number <= resume_from_row:
            continue

        # 解析行数据
        raw_data: dict[str, str] = {}
        for col_idx, field_name in col_map.items():
            if col_idx < len(row):
                raw_data[field_name] = str(row[col_idx]).strip()
            else:
                raw_data[field_name] = ""

        # 校验 trading_date
        raw_date = raw_data.get("trading_date", "")
        parsed_date = _parse_date(raw_date)
        if parsed_date is None:
            batch_anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": row_number,
                "anomaly_type": "format_error",
                "field_name": "trading_date",
                "raw_value": raw_date[:200],
                "description": f"交易日期格式错误: {raw_date}",
            })
            failed_records += 1
            processed_records += 1
            ins, dup = _flush_batch_if_needed(
                writer, job, batch_records, batch_anomalies,
                job_uuid, processed_records, success_records, failed_records, row_number,
            )
            success_records += ins
            failed_records += dup
            continue

        # 校验 period
        raw_period = raw_data.get("period", "")
        parsed_period = _parse_period(raw_period)
        if parsed_period is None:
            batch_anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": row_number,
                "anomaly_type": "format_error",
                "field_name": "period",
                "raw_value": raw_period[:200],
                "description": f"时段编号超出范围(1-96): {raw_period}",
            })
            failed_records += 1
            processed_records += 1
            ins, dup = _flush_batch_if_needed(
                writer, job, batch_records, batch_anomalies,
                job_uuid, processed_records, success_records, failed_records, row_number,
            )
            success_records += ins
            failed_records += dup
            continue

        # 校验 clearing_price
        raw_price = raw_data.get("clearing_price", "")
        parsed_price = _parse_price(raw_price)
        if parsed_price is None:
            batch_anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": row_number,
                "anomaly_type": "format_error",
                "field_name": "clearing_price",
                "raw_value": raw_price[:200],
                "description": f"出清价格格式错误: {raw_price}",
            })
            failed_records += 1
            processed_records += 1
            ins, dup = _flush_batch_if_needed(
                writer, job, batch_records, batch_anomalies,
                job_uuid, processed_records, success_records, failed_records, row_number,
            )
            success_records += ins
            failed_records += dup
            continue

        # 价格范围校验（与省份限价对比）
        if price_cap_upper is not None and price_cap_lower is not None:
            if parsed_price > price_cap_upper or parsed_price < price_cap_lower:
                batch_anomalies.append({
                    "id": uuid.uuid4(),
                    "import_job_id": job_uuid,
                    "row_number": row_number,
                    "anomaly_type": "out_of_range",
                    "field_name": "clearing_price",
                    "raw_value": str(parsed_price),
                    "description": (
                        f"出清价格超出省份限价范围"
                        f"({price_cap_lower}~{price_cap_upper}): {parsed_price}"
                    ),
                })
                failed_records += 1
                processed_records += 1
                ins, dup = _flush_batch_if_needed(
                    writer, job, batch_records, batch_anomalies,
                    job_uuid, processed_records, success_records, failed_records, row_number,
                )
                success_records += ins
                failed_records += dup
                continue

        # 有效记录加入批次
        all_trading_dates.add(parsed_date)
        batch_records.append({
            "id": uuid.uuid4(),
            "trading_date": parsed_date,
            "period": parsed_period,
            "station_id": job.station_id,
            "clearing_price": parsed_price,
            "import_job_id": job_uuid,
        })
        processed_records += 1

        # 批量处理
        if len(batch_records) >= BATCH_SIZE:
            inserted, dup_count = writer.flush_batch(
                job, batch_records, batch_anomalies, job_uuid,
                processed_records, success_records, failed_records, row_number,
            )
            success_records += inserted
            failed_records += dup_count
            batch_records.clear()
            batch_anomalies.clear()

    # 处理剩余批次
    if batch_records or batch_anomalies:
        inserted, dup_count, dup_anomalies = writer.insert_trading_records(
            batch_records, job_uuid,
        )
        writer.insert_anomalies(batch_anomalies + dup_anomalies)
        success_records += inserted
        failed_records += dup_count

    # 更新 total_records（实际数据行数，不含列头）
    job.total_records = total_records

    # 时段完整性检测
    if all_trading_dates:
        _check_period_completeness(writer, job_uuid, job.station_id, all_trading_dates)

    # 计算数据完整性百分比
    if total_records > 0:
        job.data_completeness = Decimal(str(round(success_records / total_records * 100, 2)))
    else:
        job.data_completeness = Decimal("0")

    # 更新状态为 completed
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    job.processed_records = processed_records
    job.success_records = success_records
    job.failed_records = failed_records
    job.last_processed_row = row_number

    # 写入审计日志
    audit_log = AuditLog(
        user_id=job.imported_by,
        action="complete_import_job",
        resource_type="data_import_job",
        resource_id=job.id,
        changes_after={
            "file_name": job.original_file_name,
            "total_records": job.total_records,
            "success_records": job.success_records,
            "failed_records": job.failed_records,
            "data_completeness": str(job.data_completeness),
        },
    )
    session.add(audit_log)

    session.commit()

    logger.info(
        "import_task_completed",
        job_id=str(job.id),
        total=job.total_records,
        success=job.success_records,
        failed=job.failed_records,
        completeness=str(job.data_completeness),
    )


class SyncBatchWriter:
    """同步批量写入器，封装 Celery 任务中的数据库批量操作。

    Celery worker 使用同步 SQLAlchemy 会话，与 API 层的异步 Repository 分离。
    """

    def __init__(self, session):
        self.session = session

    def insert_trading_records(
        self, records: list[dict], job_uuid: uuid.UUID,
    ) -> tuple[int, int, list[dict]]:
        """批量插入交易记录，返回 (inserted_count, duplicate_count, duplicate_anomalies)。"""
        if not records:
            return 0, 0, []

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(TradingRecord).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["station_id", "trading_date", "period"],
        )
        result = self.session.execute(stmt)
        inserted = result.rowcount
        skipped = len(records) - inserted

        anomalies: list[dict] = []
        if skipped > 0:
            anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": 0,
                "anomaly_type": "duplicate",
                "field_name": "trading_record",
                "raw_value": None,
                "description": f"本批次中 {skipped} 条重复记录已跳过（station_id + trading_date + period 重复）",
            })

        return inserted, skipped, anomalies

    def insert_anomalies(self, anomalies: list[dict]) -> None:
        """批量插入异常记录。"""
        if anomalies:
            self.session.execute(
                ImportAnomaly.__table__.insert().values(anomalies)
            )

    def flush_batch(
        self, job, batch_records: list[dict], batch_anomalies: list[dict],
        job_uuid: uuid.UUID, processed_records: int, success_records: int,
        failed_records: int, row_number: int,
    ) -> tuple[int, int]:
        """提交当前批次，返回 (inserted_count, duplicate_count)。"""
        inserted, dup_count, dup_anomalies = self.insert_trading_records(
            batch_records, job_uuid,
        )
        all_anomalies = batch_anomalies + dup_anomalies
        self.insert_anomalies(all_anomalies)

        job.processed_records = processed_records
        job.success_records = success_records + inserted
        job.failed_records = failed_records + dup_count
        job.last_processed_row = row_number
        self.session.commit()

        return inserted, dup_count


def _flush_batch_if_needed(
    writer: SyncBatchWriter, job, batch_records, batch_anomalies,
    job_uuid, processed_records, success_records, failed_records, row_number,
) -> tuple[int, int]:
    """检查是否需要提交当前批次（累计异常达到 BATCH_SIZE 时）。

    返回 (additional_success, additional_failed) 以便调用方更新计数。
    """
    if len(batch_anomalies) >= BATCH_SIZE:
        inserted, dup_count = writer.flush_batch(
            job, batch_records, batch_anomalies, job_uuid,
            processed_records, success_records, failed_records, row_number,
        )
        batch_records.clear()
        batch_anomalies.clear()
        return inserted, dup_count
    return 0, 0


def _check_period_completeness(
    writer: SyncBatchWriter, job_uuid: uuid.UUID, station_id: uuid.UUID,
    trading_dates: set[date],
):
    """检测时段完整性：每个交易日是否有完整 96 时段。"""
    from sqlalchemy import func, select

    stmt = (
        select(
            TradingRecord.trading_date,
            func.array_agg(TradingRecord.period).label("periods"),
        )
        .where(
            TradingRecord.station_id == station_id,
            TradingRecord.trading_date.in_(list(trading_dates)),
        )
        .group_by(TradingRecord.trading_date)
    )
    result = writer.session.execute(stmt)
    anomalies: list[dict] = []

    for row in result.all():
        existing_periods = set(row.periods)
        all_periods = set(range(1, 97))
        missing = sorted(all_periods - existing_periods)
        if missing:
            # 简化描述：最多列出前 10 个缺失时段
            missing_str = ", ".join(str(p) for p in missing[:10])
            if len(missing) > 10:
                missing_str += f"... (共{len(missing)}个)"
            anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": 0,
                "anomaly_type": "missing",
                "field_name": "period",
                "raw_value": None,
                "description": f"交易日 {row.trading_date} 缺少时段: {missing_str}",
            })

    writer.insert_anomalies(anomalies)
