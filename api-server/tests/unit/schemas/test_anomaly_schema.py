import pytest
from pydantic import ValidationError

from app.schemas.data_import import (
    AnomalyBulkActionRequest,
    AnomalyBulkActionResponse,
    AnomalyCorrectRequest,
    AnomalyDetailRead,
)


class TestAnomalyCorrectRequest:
    """AnomalyCorrectRequest schema 校验测试。"""

    def test_valid_corrected_value(self):
        req = AnomalyCorrectRequest(corrected_value="350.00")
        assert req.corrected_value == "350.00"

    def test_corrected_value_stripped(self):
        req = AnomalyCorrectRequest(corrected_value="  350.00  ")
        assert req.corrected_value == "350.00"

    def test_empty_corrected_value_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnomalyCorrectRequest(corrected_value="")
        assert "修正值不能为空" in str(exc_info.value)

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnomalyCorrectRequest(corrected_value="   ")
        assert "修正值不能为空" in str(exc_info.value)

    def test_missing_field_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCorrectRequest()


class TestAnomalyBulkActionRequest:
    """AnomalyBulkActionRequest schema 校验测试。"""

    def test_valid_delete_action(self):
        req = AnomalyBulkActionRequest(
            anomaly_ids=["550e8400-e29b-41d4-a716-446655440000"],
            action="delete",
        )
        assert req.action == "delete"
        assert len(req.anomaly_ids) == 1

    def test_valid_confirm_normal_action(self):
        req = AnomalyBulkActionRequest(
            anomaly_ids=["550e8400-e29b-41d4-a716-446655440000"],
            action="confirm_normal",
        )
        assert req.action == "confirm_normal"

    def test_empty_anomaly_ids_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            AnomalyBulkActionRequest(anomaly_ids=[], action="delete")
        assert "不能为空" in str(exc_info.value)

    def test_over_100_ids_rejected(self):
        ids = [f"550e8400-e29b-41d4-a716-4466554400{i:02d}" for i in range(101)]
        with pytest.raises(ValidationError) as exc_info:
            AnomalyBulkActionRequest(anomaly_ids=ids, action="delete")
        assert "100" in str(exc_info.value)

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyBulkActionRequest(
                anomaly_ids=["550e8400-e29b-41d4-a716-446655440000"],
                action="invalid_action",
            )

    def test_invalid_uuid_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyBulkActionRequest(
                anomaly_ids=["not-a-uuid"],
                action="delete",
            )

    def test_multiple_valid_ids(self):
        req = AnomalyBulkActionRequest(
            anomaly_ids=[
                "550e8400-e29b-41d4-a716-446655440000",
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ],
            action="confirm_normal",
        )
        assert len(req.anomaly_ids) == 3


class TestAnomalyBulkActionResponse:
    """AnomalyBulkActionResponse schema 测试。"""

    def test_construction(self):
        resp = AnomalyBulkActionResponse(affected_count=5, action="delete")
        assert resp.affected_count == 5
        assert resp.action == "delete"


class TestAnomalyDetailRead:
    """AnomalyDetailRead schema 测试。"""

    def test_from_attributes(self):
        class FakeAnomaly:
            id = "550e8400-e29b-41d4-a716-446655440000"
            import_job_id = "550e8400-e29b-41d4-a716-446655440001"
            row_number = 42
            anomaly_type = "format_error"
            field_name = "clearing_price"
            raw_value = "abc"
            description = "价格格式错误"
            status = "pending"
            created_at = "2026-03-01T10:00:00+08:00"
            updated_at = "2026-03-01T10:00:00+08:00"

        result = AnomalyDetailRead.model_validate(FakeAnomaly(), from_attributes=True)
        assert result.row_number == 42
        assert result.original_file_name is None
        assert result.station_id is None

    def test_with_extra_fields(self):
        data = AnomalyDetailRead(
            id="550e8400-e29b-41d4-a716-446655440000",
            import_job_id="550e8400-e29b-41d4-a716-446655440001",
            row_number=10,
            anomaly_type="missing",
            field_name="period",
            raw_value=None,
            description="缺失时段",
            status="pending",
            created_at="2026-03-01T10:00:00+08:00",
            updated_at="2026-03-01T10:00:00+08:00",
            original_file_name="test.csv",
            station_id="550e8400-e29b-41d4-a716-446655440002",
        )
        assert data.original_file_name == "test.csv"
        assert data.station_id is not None
