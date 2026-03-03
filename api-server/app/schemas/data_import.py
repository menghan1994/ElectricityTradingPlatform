from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ImportJobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
AnomalyType = Literal["missing", "format_error", "out_of_range", "duplicate"]
AnomalyStatus = Literal["pending", "confirmed_normal", "corrected", "deleted"]


# --- 导入任务 schemas ---


class ImportJobCreate(BaseModel):
    station_id: UUID


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    original_file_name: str
    file_size: int
    station_id: UUID
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
