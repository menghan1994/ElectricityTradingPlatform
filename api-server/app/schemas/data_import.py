from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

ImportJobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
ImportType = Literal["trading_data", "station_output", "storage_operation", "market_data"]
EmsFormat = Literal["standard", "sungrow", "huawei", "catl"]
AnomalyType = Literal["missing", "format_error", "out_of_range", "duplicate"]
AnomalyStatus = Literal["pending", "confirmed_normal", "corrected", "deleted"]


# --- 导入任务 schemas ---


class ImportJobCreate(BaseModel):
    station_id: UUID
    import_type: ImportType = "trading_data"
    ems_format: EmsFormat | None = None


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    original_file_name: str
    file_size: int
    station_id: UUID
    import_type: ImportType
    ems_format: EmsFormat | None
    status: ImportJobStatus
    total_records: int
    processed_records: int
    success_records: int
    failed_records: int
    data_completeness: Decimal
    last_processed_row: int
    celery_task_id: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    imported_by: UUID
    created_at: datetime
    updated_at: datetime


class ImportJobListResponse(BaseModel):
    items: list[ImportJobRead]
    total: int
    page: int
    page_size: int


# --- 异常记录 schemas ---


class ImportAnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    import_job_id: UUID
    row_number: int
    anomaly_type: AnomalyType
    field_name: str
    raw_value: str | None
    description: str
    status: AnomalyStatus
    created_at: datetime
    updated_at: datetime


class ImportAnomalySummary(BaseModel):
    anomaly_type: str
    count: int


class ImportResultRead(BaseModel):
    total_records: int
    success_records: int
    failed_records: int
    data_completeness: Decimal
    anomaly_summary: list[ImportAnomalySummary]


class ImportAnomalyListResponse(BaseModel):
    items: list[ImportAnomalyRead]
    total: int
    page: int
    page_size: int


# --- 异常管理 schemas (Story 2.4) ---


class AnomalyCorrectRequest(BaseModel):
    corrected_value: str

    @field_validator("corrected_value")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("修正值不能为空")
        return v.strip()


class AnomalyBulkActionRequest(BaseModel):
    anomaly_ids: list[UUID]
    action: Literal["delete", "confirm_normal"]

    @field_validator("anomaly_ids")
    @classmethod
    def validate_non_empty(cls, v: list[UUID]) -> list[UUID]:
        if not v:
            raise ValueError("anomaly_ids 不能为空")
        if len(v) > 100:
            raise ValueError("单次批量操作最多 100 条")
        return v


class AnomalyBulkActionResponse(BaseModel):
    affected_count: int
    action: str


class AnomalyDetailRead(ImportAnomalyRead):
    """扩展 ImportAnomalyRead，关联 import_job 的文件名和电站信息。"""

    original_file_name: str | None = None
    station_id: UUID | None = None


# --- 电站出力数据 schemas ---


class StationOutputRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trading_date: date
    period: int
    station_id: UUID
    actual_output_kw: Decimal
    import_job_id: UUID
    created_at: datetime


class StationOutputRecordListResponse(BaseModel):
    items: list[StationOutputRecordRead]
    total: int
    page: int
    page_size: int


# --- 储能运行数据 schemas ---


class StorageOperationRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trading_date: date
    period: int
    device_id: UUID
    soc: Decimal
    charge_power_kw: Decimal
    discharge_power_kw: Decimal
    cycle_count: int
    import_job_id: UUID
    created_at: datetime


class StorageOperationRecordListResponse(BaseModel):
    items: list[StorageOperationRecordRead]
    total: int
    page: int
    page_size: int
