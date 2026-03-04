import pytest
from pydantic import ValidationError

from app.schemas.data_import import (
    ImportJobCreate,
    ImportJobRead,
    StationOutputRecordRead,
    StorageOperationRecordRead,
)


class TestImportJobCreate:
    """ImportJobCreate schema 校验测试 — import_type / ems_format 扩展。"""

    def test_default_import_type(self):
        req = ImportJobCreate(station_id="550e8400-e29b-41d4-a716-446655440000")
        assert req.import_type == "trading_data"
        assert req.ems_format is None

    def test_station_output_type(self):
        req = ImportJobCreate(
            station_id="550e8400-e29b-41d4-a716-446655440000",
            import_type="station_output",
        )
        assert req.import_type == "station_output"

    def test_storage_operation_with_ems_format(self):
        req = ImportJobCreate(
            station_id="550e8400-e29b-41d4-a716-446655440000",
            import_type="storage_operation",
            ems_format="sungrow",
        )
        assert req.import_type == "storage_operation"
        assert req.ems_format == "sungrow"

    def test_invalid_import_type_rejected(self):
        with pytest.raises(ValidationError):
            ImportJobCreate(
                station_id="550e8400-e29b-41d4-a716-446655440000",
                import_type="invalid_type",
            )

    def test_invalid_ems_format_rejected(self):
        with pytest.raises(ValidationError):
            ImportJobCreate(
                station_id="550e8400-e29b-41d4-a716-446655440000",
                import_type="storage_operation",
                ems_format="unknown_vendor",
            )

    def test_all_valid_import_types(self):
        for t in ("trading_data", "station_output", "storage_operation"):
            req = ImportJobCreate(
                station_id="550e8400-e29b-41d4-a716-446655440000",
                import_type=t,
            )
            assert req.import_type == t

    def test_all_valid_ems_formats(self):
        for fmt in ("standard", "sungrow", "huawei", "catl"):
            req = ImportJobCreate(
                station_id="550e8400-e29b-41d4-a716-446655440000",
                import_type="storage_operation",
                ems_format=fmt,
            )
            assert req.ems_format == fmt


class TestStationOutputRecordRead:
    """StationOutputRecordRead schema 测试。"""

    def test_from_attributes(self):
        class FakeRecord:
            id = "550e8400-e29b-41d4-a716-446655440000"
            trading_date = "2026-03-01"
            period = 48
            station_id = "550e8400-e29b-41d4-a716-446655440001"
            actual_output_kw = 1500.50
            import_job_id = "550e8400-e29b-41d4-a716-446655440002"
            created_at = "2026-03-01T10:00:00+08:00"

        result = StationOutputRecordRead.model_validate(FakeRecord(), from_attributes=True)
        assert result.period == 48
        from datetime import date
        assert result.trading_date == date(2026, 3, 1)

    def test_construction(self):
        record = StationOutputRecordRead(
            id="550e8400-e29b-41d4-a716-446655440000",
            trading_date="2026-03-01",
            period=1,
            station_id="550e8400-e29b-41d4-a716-446655440001",
            actual_output_kw="1200.00",
            import_job_id="550e8400-e29b-41d4-a716-446655440002",
            created_at="2026-03-01T10:00:00+08:00",
        )
        assert record.period == 1


class TestStorageOperationRecordRead:
    """StorageOperationRecordRead schema 测试。"""

    def test_from_attributes(self):
        class FakeRecord:
            id = "550e8400-e29b-41d4-a716-446655440000"
            trading_date = "2026-03-01"
            period = 24
            device_id = "550e8400-e29b-41d4-a716-446655440001"
            soc = 0.8500
            charge_power_kw = 100.00
            discharge_power_kw = 0.00
            cycle_count = 150
            import_job_id = "550e8400-e29b-41d4-a716-446655440002"
            created_at = "2026-03-01T10:00:00+08:00"

        result = StorageOperationRecordRead.model_validate(FakeRecord(), from_attributes=True)
        assert result.period == 24
        assert result.cycle_count == 150

    def test_construction(self):
        record = StorageOperationRecordRead(
            id="550e8400-e29b-41d4-a716-446655440000",
            trading_date="2026-03-01",
            period=1,
            device_id="550e8400-e29b-41d4-a716-446655440001",
            soc="0.9500",
            charge_power_kw="50.00",
            discharge_power_kw="0.00",
            cycle_count=100,
            import_job_id="550e8400-e29b-41d4-a716-446655440002",
            created_at="2026-03-01T10:00:00+08:00",
        )
        assert record.cycle_count == 100
