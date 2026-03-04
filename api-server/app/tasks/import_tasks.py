import csv
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import structlog

from app.core.config import settings
from app.core.database import get_sync_session_factory
from app.models.audit import AuditLog
from app.models.data_import import (
    DataImportJob,
    ImportAnomaly,
    StationOutputRecord,
    StorageOperationRecord,
    TradingRecord,
)
from app.models.market_rule import ProvinceMarketRule
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()

BATCH_SIZE = 1000
PERIODS_PER_DAY = 96

# 列头映射：支持中英文
COLUMN_MAPPING = {
    "交易日期": "trading_date",
    "时段": "period",
    "出清价格": "clearing_price",
    "trading_date": "trading_date",
    "period": "period",
    "clearing_price": "clearing_price",
}

STATION_OUTPUT_COLUMN_MAPPING = {
    "交易日期": "trading_date",
    "时段": "period",
    "实际出力": "actual_output_kw",
    "实际出力kw": "actual_output_kw",
    "实际出力(kw)": "actual_output_kw",
    "电站id": "station_id_col",
    "station_id": "station_id_col",
    "trading_date": "trading_date",
    "period": "period",
    "actual_output_kw": "actual_output_kw",
}


# =====================================================
# 通用解析工具函数
# =====================================================

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
        if 1 <= val <= PERIODS_PER_DAY:
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


def _parse_output_kw(raw: str) -> Decimal | None:
    try:
        val = Decimal(raw.strip())
        if val.is_nan() or val.is_infinite() or val < 0:
            return None
        return val
    except (InvalidOperation, ValueError, TypeError):
        return None


def _detect_csv_encoding(file_path: Path) -> str:
    """检测 CSV 文件编码，先尝试 UTF-8，再尝试 GBK。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            with open(file_path, encoding=encoding) as f:
                f.read(4096)
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


def _open_file_rows(file_path: Path):
    """根据文件扩展名选择读取方式。"""
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_rows(file_path)
    elif suffix == ".xlsx":
        return _read_xlsx_rows(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")


def _map_columns(
    header_row: list[str],
    column_mapping: dict[str, str],
    required_fields: set[str],
) -> dict[int, str] | None:
    """将列头映射为标准字段名，返回 {列索引: 字段名}。"""
    col_map: dict[int, str] = {}
    found_fields: set[str] = set()

    for i, col in enumerate(header_row):
        cleaned = col.strip().lower()
        for key, field in column_mapping.items():
            if cleaned == key.lower():
                col_map[i] = field
                found_fields.add(field)
                break

    if not required_fields.issubset(found_fields):
        return None
    return col_map


# =====================================================
# 通用批处理基础设施
# =====================================================

class ImportContext:
    """封装导入过程中的状态跟踪。"""

    def __init__(self, session, job: DataImportJob, resume_from_row: int):
        self.session = session
        self.job = job
        self.job_uuid = job.id
        self.resume_from_row = resume_from_row
        self.row_number = 0
        self.total_records = 0
        self.success_records = job.success_records if resume_from_row > 0 else 0
        self.failed_records = job.failed_records if resume_from_row > 0 else 0
        self.processed_records = job.processed_records if resume_from_row > 0 else 0
        self.batch_records: list[dict] = []
        self.batch_anomalies: list[dict] = []
        self.all_trading_dates: set[date] = set()

    def add_anomaly(self, anomaly_type: str, field_name: str,
                    raw_value: str | None, description: str) -> None:
        self.batch_anomalies.append({
            "id": uuid.uuid4(),
            "import_job_id": self.job_uuid,
            "row_number": self.row_number,
            "anomaly_type": anomaly_type,
            "field_name": field_name,
            "raw_value": raw_value[:200] if raw_value else None,
            "description": description,
        })
        self.failed_records += 1
        self.processed_records += 1

    def flush_batch(self, insert_fn) -> None:
        """提交当前批次的数据和异常。"""
        if self.batch_records:
            inserted, skipped = insert_fn(self.batch_records)
            self.success_records += inserted
            if skipped > 0:
                self.batch_anomalies.append({
                    "id": uuid.uuid4(),
                    "import_job_id": self.job_uuid,
                    "row_number": 0,
                    "anomaly_type": "duplicate",
                    "field_name": "record",
                    "raw_value": None,
                    "description": f"本批次中 {skipped} 条重复记录已跳过",
                })
                self.failed_records += skipped

        if self.batch_anomalies:
            self.session.execute(
                ImportAnomaly.__table__.insert().values(self.batch_anomalies)
            )

        self.job.processed_records = self.processed_records
        self.job.success_records = self.success_records
        self.job.failed_records = self.failed_records
        self.job.last_processed_row = self.row_number
        self.session.commit()
        self.batch_records.clear()
        self.batch_anomalies.clear()

    def should_flush(self) -> bool:
        return len(self.batch_records) >= BATCH_SIZE or len(self.batch_anomalies) >= BATCH_SIZE

    def finalize(self, audit_action: str, extra_audit: dict | None = None) -> None:
        """完成导入：更新统计、写审计日志。"""
        self.job.total_records = self.total_records
        if self.total_records > 0:
            self.job.data_completeness = Decimal(
                str(round(self.success_records / self.total_records * 100, 2))
            )
        else:
            self.job.data_completeness = Decimal("0")

        self.job.status = "completed"
        self.job.completed_at = datetime.now(timezone.utc)
        self.job.processed_records = self.processed_records
        self.job.success_records = self.success_records
        self.job.failed_records = self.failed_records
        self.job.last_processed_row = self.row_number

        audit_data = {
            "file_name": self.job.original_file_name,
            "total_records": self.job.total_records,
            "success_records": self.job.success_records,
            "failed_records": self.job.failed_records,
            "data_completeness": str(self.job.data_completeness),
        }
        if extra_audit:
            audit_data.update(extra_audit)

        audit_log = AuditLog(
            user_id=self.job.imported_by,
            action=audit_action,
            resource_type="data_import_job",
            resource_id=self.job.id,
            changes_after=audit_data,
        )
        self.session.add(audit_log)
        self.session.commit()


def _init_import(session, task, job_id: str) -> DataImportJob:
    """通用导入初始化：加载 job 并标记为 processing。"""
    job_uuid = uuid.UUID(job_id)
    job = session.get(DataImportJob, job_uuid)
    if not job:
        raise ValueError(f"Import job {job_id} not found")

    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.celery_task_id = task.request.id
    session.commit()
    return job


def _get_file_path(job: DataImportJob) -> Path:
    """获取导入文件路径，不在错误消息中泄漏完整路径。"""
    file_path = Path(settings.DATA_IMPORT_DIR) / job.file_name
    if not file_path.exists():
        raise FileNotFoundError(f"导入文件不存在，请确认文件是否已被清理")
    return file_path


def _parse_row_data(row: list[str], col_map: dict[int, str]) -> dict[str, str]:
    """解析一行数据为字段字典。"""
    raw_data: dict[str, str] = {}
    for col_idx, field_name in col_map.items():
        if col_idx < len(row):
            raw_data[field_name] = str(row[col_idx]).strip()
        else:
            raw_data[field_name] = ""
    return raw_data


def _validate_date_period(ctx: ImportContext, raw_data: dict) -> tuple[date, int] | None:
    """校验 trading_date 和 period，返回 (parsed_date, parsed_period) 或 None。"""
    raw_date = raw_data.get("trading_date", "")
    parsed_date = _parse_date(raw_date)
    if parsed_date is None:
        ctx.add_anomaly("format_error", "trading_date", raw_date,
                        f"交易日期格式错误: {raw_date}")
        return None

    raw_period = raw_data.get("period", "")
    parsed_period = _parse_period(raw_period)
    if parsed_period is None:
        ctx.add_anomaly("format_error", "period", raw_period,
                        f"时段编号超出范围(1-{PERIODS_PER_DAY}): {raw_period}")
        return None

    return parsed_date, parsed_period


def _check_period_completeness(
    session, job_uuid: uuid.UUID, entity_id: uuid.UUID,
    trading_dates: set[date], record_model, id_field_name: str,
    entity_label: str = "",
):
    """通用时段完整性检测。"""
    from sqlalchemy import func, select

    id_col = getattr(record_model, id_field_name)
    stmt = (
        select(
            record_model.trading_date,
            func.array_agg(record_model.period).label("periods"),
        )
        .where(
            id_col == entity_id,
            record_model.trading_date.in_(list(trading_dates)),
        )
        .group_by(record_model.trading_date)
    )
    result = session.execute(stmt)
    anomalies: list[dict] = []

    for row in result.all():
        existing_periods = set(row.periods)
        missing = sorted(set(range(1, PERIODS_PER_DAY + 1)) - existing_periods)
        if missing:
            missing_str = ", ".join(str(p) for p in missing[:10])
            if len(missing) > 10:
                missing_str += f"... (共{len(missing)}个)"
            desc = f"交易日 {row.trading_date} "
            if entity_label:
                desc += f"{entity_label}"
            desc += f"缺少时段: {missing_str}"
            anomalies.append({
                "id": uuid.uuid4(),
                "import_job_id": job_uuid,
                "row_number": 0,
                "anomaly_type": "missing",
                "field_name": "period",
                "raw_value": None,
                "description": desc,
            })

    if anomalies:
        session.execute(ImportAnomaly.__table__.insert().values(anomalies))


def _run_import_task(task_fn, job_id: str, **kwargs):
    """通用 Celery 任务执行包装器。"""
    SyncSessionLocal = get_sync_session_factory()
    session = SyncSessionLocal()
    try:
        task_fn(session, **kwargs)
    except Exception as e:
        session.rollback()
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


# =====================================================
# 交易数据导入
# =====================================================

@celery_app.task(bind=True, max_retries=0)
def process_trading_data_import(self, job_id: str, resume_from_row: int = 0):
    """后台处理交易数据导入。"""
    _run_import_task(
        lambda session, **kw: _execute_import(session, self, job_id, resume_from_row),
        job_id,
    )


def _insert_trading_records(session, records: list[dict]) -> tuple[int, int]:
    """批量插入交易记录，返回 (inserted, skipped)。"""
    if not records:
        return 0, 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(TradingRecord).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["station_id", "trading_date", "period"],
    )
    result = session.execute(stmt)
    inserted = result.rowcount
    return inserted, len(records) - inserted


def _execute_import(session, task, job_id: str, resume_from_row: int):
    """核心交易数据导入逻辑。"""
    job = _init_import(session, task, job_id)

    # 获取省份市场规则
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

    file_path = _get_file_path(job)
    rows = _open_file_rows(file_path)

    header_row = next(rows, None)
    if header_row is None:
        raise ValueError("文件为空，无法读取列头")

    col_map = _map_columns(header_row, COLUMN_MAPPING,
                           {"trading_date", "period", "clearing_price"})
    if col_map is None:
        raise ValueError("列头映射失败：需要包含 trading_date/交易日期、period/时段、clearing_price/出清价格")

    ctx = ImportContext(session, job, resume_from_row)
    insert_fn = lambda records: _insert_trading_records(session, records)

    for row in rows:
        ctx.row_number += 1
        ctx.total_records += 1
        if ctx.row_number <= resume_from_row:
            continue

        raw_data = _parse_row_data(row, col_map)

        dp = _validate_date_period(ctx, raw_data)
        if dp is None:
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue
        parsed_date, parsed_period = dp

        # 校验 clearing_price
        raw_price = raw_data.get("clearing_price", "")
        parsed_price = _parse_price(raw_price)
        if parsed_price is None:
            ctx.add_anomaly("format_error", "clearing_price", raw_price,
                            f"出清价格格式错误: {raw_price}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        # 价格范围校验
        if price_cap_upper is not None and price_cap_lower is not None:
            if parsed_price > price_cap_upper or parsed_price < price_cap_lower:
                ctx.add_anomaly(
                    "out_of_range", "clearing_price", str(parsed_price),
                    f"出清价格超出省份限价范围({price_cap_lower}~{price_cap_upper}): {parsed_price}",
                )
                if ctx.should_flush():
                    ctx.flush_batch(insert_fn)
                continue

        ctx.all_trading_dates.add(parsed_date)
        ctx.batch_records.append({
            "id": uuid.uuid4(),
            "trading_date": parsed_date,
            "period": parsed_period,
            "station_id": job.station_id,
            "clearing_price": parsed_price,
            "import_job_id": ctx.job_uuid,
        })
        ctx.processed_records += 1

        if ctx.should_flush():
            ctx.flush_batch(insert_fn)

    # 处理剩余批次
    ctx.flush_batch(insert_fn)

    # 时段完整性检测
    if ctx.all_trading_dates:
        _check_period_completeness(
            session, ctx.job_uuid, job.station_id, ctx.all_trading_dates,
            TradingRecord, "station_id",
        )

    ctx.finalize("complete_import_job")

    logger.info(
        "import_task_completed",
        job_id=str(job.id),
        total=job.total_records,
        success=job.success_records,
        failed=job.failed_records,
        completeness=str(job.data_completeness),
    )


# =====================================================
# 电站出力数据导入
# =====================================================

@celery_app.task(bind=True, max_retries=0)
def process_station_output_import(self, job_id: str, resume_from_row: int = 0):
    """后台处理电站出力数据导入。"""
    _run_import_task(
        lambda session, **kw: _execute_station_output_import(session, self, job_id, resume_from_row),
        job_id,
    )


def _insert_output_records(session, records: list[dict]) -> tuple[int, int]:
    """批量插入电站出力记录，返回 (inserted, skipped)。"""
    if not records:
        return 0, 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(StationOutputRecord).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["station_id", "trading_date", "period"],
    )
    result = session.execute(stmt)
    inserted = result.rowcount
    return inserted, len(records) - inserted


def _execute_station_output_import(session, task, job_id: str, resume_from_row: int):
    job = _init_import(session, task, job_id)

    file_path = _get_file_path(job)
    rows = _open_file_rows(file_path)

    header_row = next(rows, None)
    if header_row is None:
        raise ValueError("文件为空，无法读取列头")

    col_map = _map_columns(header_row, STATION_OUTPUT_COLUMN_MAPPING,
                           {"trading_date", "period", "actual_output_kw"})
    if col_map is None:
        raise ValueError("列头映射失败：需要包含 trading_date/交易日期、period/时段、actual_output_kw/实际出力")

    ctx = ImportContext(session, job, resume_from_row)
    insert_fn = lambda records: _insert_output_records(session, records)

    for row in rows:
        ctx.row_number += 1
        ctx.total_records += 1
        if ctx.row_number <= resume_from_row:
            continue

        raw_data = _parse_row_data(row, col_map)

        dp = _validate_date_period(ctx, raw_data)
        if dp is None:
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue
        parsed_date, parsed_period = dp

        # 校验 actual_output_kw
        raw_output = raw_data.get("actual_output_kw", "")
        parsed_output = _parse_output_kw(raw_output)
        if parsed_output is None:
            ctx.add_anomaly("format_error", "actual_output_kw", raw_output,
                            f"实际出力格式错误或为负值: {raw_output}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        ctx.all_trading_dates.add(parsed_date)
        ctx.batch_records.append({
            "id": uuid.uuid4(),
            "trading_date": parsed_date,
            "period": parsed_period,
            "station_id": job.station_id,
            "actual_output_kw": parsed_output,
            "import_job_id": ctx.job_uuid,
        })
        ctx.processed_records += 1

        if ctx.should_flush():
            ctx.flush_batch(insert_fn)

    # 处理剩余批次
    ctx.flush_batch(insert_fn)

    # 时段完整性检测
    if ctx.all_trading_dates:
        _check_period_completeness(
            session, ctx.job_uuid, job.station_id, ctx.all_trading_dates,
            StationOutputRecord, "station_id", "出力数据",
        )

    ctx.finalize("complete_station_output_import")

    logger.info(
        "station_output_import_completed",
        job_id=str(job.id),
        total=job.total_records,
        success=job.success_records,
        failed=job.failed_records,
    )


# =====================================================
# 储能运行数据导入
# =====================================================

@celery_app.task(bind=True, max_retries=0)
def process_storage_operation_import(
    self, job_id: str, resume_from_row: int = 0, ems_format: str = "standard",
):
    """后台处理储能运行数据导入。"""
    _run_import_task(
        lambda session, **kw: _execute_storage_operation_import(
            session, self, job_id, resume_from_row, ems_format,
        ),
        job_id,
    )


def _insert_storage_records(session, records: list[dict]) -> tuple[int, int]:
    """批量插入储能运行记录，返回 (inserted, skipped)。"""
    if not records:
        return 0, 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = pg_insert(StorageOperationRecord).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["device_id", "trading_date", "period"],
    )
    result = session.execute(stmt)
    inserted = result.rowcount
    return inserted, len(records) - inserted


def _execute_storage_operation_import(
    session, task, job_id: str, resume_from_row: int, ems_format: str,
):
    from app.services.ems_adapters import get_adapter

    job = _init_import(session, task, job_id)

    # 获取电站下的储能设备（按创建时间排序取第一个活跃设备）
    from sqlalchemy import select as sa_select

    device_stmt = (
        sa_select(StorageDevice)
        .where(
            StorageDevice.station_id == job.station_id,
            StorageDevice.is_active.is_(True),
        )
        .order_by(StorageDevice.created_at)
        .limit(1)
    )
    device = session.execute(device_stmt).scalar_one_or_none()
    if not device:
        raise ValueError(f"电站 {job.station_id} 没有活跃的储能设备")
    device_id = device.id

    # 获取 EMS 适配器
    adapter = get_adapter(ems_format)
    column_mapping = adapter.get_column_mapping()

    file_path = _get_file_path(job)
    rows = _open_file_rows(file_path)

    header_row = next(rows, None)
    if header_row is None:
        raise ValueError("文件为空，无法读取列头")

    # 使用适配器列映射
    col_map: dict[int, str] = {}
    for i, col in enumerate(header_row):
        cleaned = col.strip()
        for vendor_col, std_field in column_mapping.items():
            if cleaned == vendor_col or cleaned.lower() == vendor_col.lower():
                col_map[i] = std_field
                break

    required_fields = {"trading_date", "period", "soc"}
    found = set(col_map.values())
    if not required_fields.issubset(found):
        raise ValueError(
            f"列头映射失败（{ems_format} 格式）：需要 trading_date, period, soc 对应的列"
        )

    ctx = ImportContext(session, job, resume_from_row)
    insert_fn = lambda records: _insert_storage_records(session, records)
    latest_soc: Decimal | None = None
    latest_date_period: tuple[date, int] | None = None

    for row in rows:
        ctx.row_number += 1
        ctx.total_records += 1
        if ctx.row_number <= resume_from_row:
            continue

        raw_data = _parse_row_data(row, col_map)

        dp = _validate_date_period(ctx, raw_data)
        if dp is None:
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue
        parsed_date, parsed_period = dp

        # 校验并转换 SOC
        raw_soc = raw_data.get("soc", "")
        try:
            parsed_soc = adapter.transform_soc(raw_soc)
            if parsed_soc < 0 or parsed_soc > 1:
                raise ValueError("SOC out of range")
        except (InvalidOperation, ValueError, TypeError):
            ctx.add_anomaly("out_of_range", "soc", raw_soc,
                            f"SOC 值无效或超出范围(0-1): {raw_soc}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        # 解析可选字段
        raw_charge = raw_data.get("charge_power_kw", "0")
        raw_discharge = raw_data.get("discharge_power_kw", "0")
        raw_cycle = raw_data.get("cycle_count", "0")

        try:
            parsed_charge = adapter.transform_power(raw_charge) if raw_charge else Decimal("0")
            if parsed_charge < 0:
                raise ValueError("negative charge")
        except (InvalidOperation, ValueError, TypeError):
            ctx.add_anomaly("format_error", "charge_power_kw", raw_charge,
                            f"充电功率格式错误: {raw_charge}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        try:
            parsed_discharge = adapter.transform_power(raw_discharge) if raw_discharge else Decimal("0")
            if parsed_discharge < 0:
                raise ValueError("negative discharge")
        except (InvalidOperation, ValueError, TypeError):
            ctx.add_anomaly("format_error", "discharge_power_kw", raw_discharge,
                            f"放电功率格式错误: {raw_discharge}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        try:
            parsed_cycle = adapter.transform_cycle_count(raw_cycle) if raw_cycle else 0
            if parsed_cycle < 0:
                raise ValueError("negative cycle")
        except (ValueError, TypeError):
            ctx.add_anomaly("format_error", "cycle_count", raw_cycle,
                            f"循环次数格式错误: {raw_cycle}")
            if ctx.should_flush():
                ctx.flush_batch(insert_fn)
            continue

        ctx.batch_records.append({
            "id": uuid.uuid4(),
            "trading_date": parsed_date,
            "period": parsed_period,
            "device_id": device_id,
            "soc": parsed_soc,
            "charge_power_kw": parsed_charge,
            "discharge_power_kw": parsed_discharge,
            "cycle_count": parsed_cycle,
            "import_job_id": ctx.job_uuid,
        })
        ctx.processed_records += 1

        # 追踪最新的 SOC 值
        if latest_date_period is None or (parsed_date, parsed_period) > latest_date_period:
            latest_date_period = (parsed_date, parsed_period)
            latest_soc = parsed_soc

        if ctx.should_flush():
            ctx.flush_batch(insert_fn)

    # 处理剩余批次
    ctx.flush_batch(insert_fn)

    # 更新设备最新 SOC
    if latest_soc is not None:
        device.current_soc = latest_soc
        logger.info(
            "device_soc_updated",
            device_id=str(device_id),
            current_soc=str(latest_soc),
        )

    # 时段完整性检测
    if ctx.all_trading_dates:
        _check_period_completeness(
            session, ctx.job_uuid, device_id, ctx.all_trading_dates,
            StorageOperationRecord, "device_id", "储能运行数据",
        )

    ctx.finalize(
        "complete_storage_operation_import",
        extra_audit={
            "device_id": str(device_id),
            "ems_format": ems_format,
            "latest_soc": str(latest_soc) if latest_soc is not None else None,
        },
    )

    logger.info(
        "storage_operation_import_completed",
        job_id=str(job.id),
        total=job.total_records,
        success=job.success_records,
        failed=job.failed_records,
        ems_format=ems_format,
    )
