from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.data_import import (
    ImportAnomalyListResponse,
    ImportAnomalyRead,
    ImportJobCreate,
    ImportJobListResponse,
    ImportJobRead,
    ImportResultRead,
)


class TestImportJobRead:
    """ImportJobRead schema 转换测试。"""

    def test_from_attributes(self):
        """验证 from_attributes=True 模式可以从类属性对象转换。"""

        class FakeJob:
            id = "550e8400-e29b-41d4-a716-446655440000"
            file_name = "abc/test.csv"
            original_file_name = "test.csv"
            file_size = 1024
            station_id = "550e8400-e29b-41d4-a716-446655440001"
            status = "completed"
            total_records = 100
            processed_records = 100
            success_records = 95
            failed_records = 5
            data_completeness = Decimal("95.00")
            last_processed_row = 100
            celery_task_id = "task-123"
            error_message = None
            started_at = "2026-03-01T10:00:00+08:00"
            completed_at = "2026-03-01T10:05:00+08:00"
            imported_by = "550e8400-e29b-41d4-a716-446655440002"
            created_at = "2026-03-01T09:59:50+08:00"
            updated_at = "2026-03-01T10:05:00+08:00"

        result = ImportJobRead.model_validate(FakeJob(), from_attributes=True)
        assert result.original_file_name == "test.csv"
        assert result.total_records == 100
        assert result.success_records == 95
        assert result.failed_records == 5
        assert result.status == "completed"

    def test_uuid_coercion_from_string(self):
        """验证字符串 UUID 正确转换为 UUID 类型。"""

        class FakeJob:
            id = "550e8400-e29b-41d4-a716-446655440000"
            file_name = "abc/test.csv"
            original_file_name = "test.csv"
            file_size = 1024
            station_id = "550e8400-e29b-41d4-a716-446655440001"
            status = "pending"
            total_records = 0
            processed_records = 0
            success_records = 0
            failed_records = 0
            data_completeness = Decimal("0")
            last_processed_row = 0
            celery_task_id = None
            error_message = None
            started_at = None
            completed_at = None
            imported_by = "550e8400-e29b-41d4-a716-446655440002"
            created_at = "2026-03-01T09:59:50+08:00"
            updated_at = "2026-03-01T09:59:50+08:00"

        result = ImportJobRead.model_validate(FakeJob(), from_attributes=True)
        assert isinstance(result.id, UUID)
        assert isinstance(result.station_id, UUID)
        assert isinstance(result.imported_by, UUID)
        assert result.celery_task_id is None
        assert result.started_at is None

    def test_invalid_status_rejected(self):
        """验证无效 status 字符串被 Literal 类型拒绝。"""
        with pytest.raises(ValidationError):
            ImportJobRead(
                id="550e8400-e29b-41d4-a716-446655440000",
                file_name="test.csv",
                original_file_name="test.csv",
                file_size=1024,
                station_id="550e8400-e29b-41d4-a716-446655440001",
                status="invalid_status",
                total_records=0,
                processed_records=0,
                success_records=0,
                failed_records=0,
                data_completeness=Decimal("0"),
                last_processed_row=0,
                celery_task_id=None,
                error_message=None,
                started_at=None,
                completed_at=None,
                imported_by="550e8400-e29b-41d4-a716-446655440002",
                created_at="2026-03-01T09:59:50+08:00",
                updated_at="2026-03-01T09:59:50+08:00",
            )


class TestImportJobCreate:
    """ImportJobCreate schema 测试。"""

    def test_valid_station_id(self):
        result = ImportJobCreate(station_id="550e8400-e29b-41d4-a716-446655440000")
        assert isinstance(result.station_id, UUID)

    def test_invalid_uuid_rejected(self):
        with pytest.raises(ValidationError):
            ImportJobCreate(station_id="not-a-uuid")


class TestImportAnomalyRead:
    """ImportAnomalyRead schema 转换测试。"""

    def test_from_attributes(self):
        class FakeAnomaly:
            id = "550e8400-e29b-41d4-a716-446655440000"
            import_job_id = "550e8400-e29b-41d4-a716-446655440001"
            row_number = 42
            anomaly_type = "format_error"
            field_name = "trading_date"
            raw_value = "2025/13/01"
            description = "交易日期格式错误"
            status = "pending"
            created_at = "2026-03-01T10:00:00+08:00"
            updated_at = "2026-03-01T10:00:00+08:00"

        result = ImportAnomalyRead.model_validate(FakeAnomaly(), from_attributes=True)
        assert result.row_number == 42
        assert result.anomaly_type == "format_error"
        assert result.field_name == "trading_date"
        assert isinstance(result.id, UUID)

    def test_invalid_anomaly_type_rejected(self):
        with pytest.raises(ValidationError):
            ImportAnomalyRead(
                id="550e8400-e29b-41d4-a716-446655440000",
                import_job_id="550e8400-e29b-41d4-a716-446655440001",
                row_number=1,
                anomaly_type="unknown_type",
                field_name="price",
                raw_value=None,
                description="test",
                status="pending",
                created_at="2026-03-01T10:00:00+08:00",
                updated_at="2026-03-01T10:00:00+08:00",
            )


class TestImportResultRead:
    """ImportResultRead schema 测试。"""

    def test_construction(self):
        result = ImportResultRead(
            total_records=1000,
            success_records=980,
            failed_records=20,
            data_completeness=Decimal("98.00"),
            anomaly_summary=[],
        )
        assert result.total_records == 1000
        assert result.data_completeness == Decimal("98.00")
        assert result.anomaly_summary == []


class TestImportAnomalyListResponse:
    """ImportAnomalyListResponse schema 测试。"""

    def test_construction(self):
        response = ImportAnomalyListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
        )
        assert response.total == 0
        assert response.page == 1


class TestImportJobListResponse:
    """ImportJobListResponse schema 测试。"""

    def test_construction(self):
        response = ImportJobListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
        )
        assert response.total == 0
