from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.prediction import (
    ConnectionTestResult,
    PredictionModelCreate,
    PredictionModelListResponse,
    PredictionModelRead,
    PredictionModelStatus,
    PredictionModelUpdate,
)


class TestPredictionModelCreate:
    """PredictionModelCreate schema 测试。"""

    def test_valid_create(self):
        result = PredictionModelCreate(
            model_name="风电预测模型",
            api_endpoint="https://api.example.com/predict",
            station_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert result.model_name == "风电预测模型"
        assert result.model_type == "wind"
        assert result.api_auth_type == "api_key"
        assert result.timeout_seconds == 30
        assert result.call_frequency_cron == "0 6,12 * * *"

    def test_all_fields(self):
        result = PredictionModelCreate(
            model_name="光伏预测",
            model_type="solar",
            api_endpoint="https://api.example.com/predict",
            api_key="secret-key",
            api_auth_type="bearer",
            call_frequency_cron="0 */6 * * *",
            timeout_seconds=60,
            station_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert result.model_type == "solar"
        assert result.api_key == "secret-key"
        assert result.api_auth_type == "bearer"
        assert result.timeout_seconds == 60

    def test_empty_model_name_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelCreate(
                model_name="  ",
                api_endpoint="https://api.example.com",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_empty_api_endpoint_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="  ",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_invalid_timeout_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="https://api.example.com",
                station_id="550e8400-e29b-41d4-a716-446655440000",
                timeout_seconds=0,
            )

    def test_timeout_too_large_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="https://api.example.com",
                station_id="550e8400-e29b-41d4-a716-446655440000",
                timeout_seconds=500,
            )

    def test_invalid_model_type_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="https://api.example.com",
                station_id="550e8400-e29b-41d4-a716-446655440000",
                model_type="invalid",
            )

    def test_ssrf_localhost_rejected(self):
        with pytest.raises(ValidationError, match="本地地址"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="http://localhost:8080/predict",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_ssrf_metadata_rejected(self):
        with pytest.raises(ValidationError, match="内部网络地址"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="http://169.254.169.254/latest/meta-data/",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_ssrf_private_10_rejected(self):
        with pytest.raises(ValidationError, match="内部网络地址"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="http://10.0.0.1:6379/",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_ssrf_private_172_rejected(self):
        with pytest.raises(ValidationError, match="内部网络地址"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="http://172.16.0.1:8080/predict",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_ssrf_private_192_rejected(self):
        with pytest.raises(ValidationError, match="内部网络地址"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="http://192.168.1.1/admin",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_invalid_scheme_rejected(self):
        with pytest.raises(ValidationError, match="http://"):
            PredictionModelCreate(
                model_name="测试模型",
                api_endpoint="ftp://file-server.com/data",
                station_id="550e8400-e29b-41d4-a716-446655440000",
            )


class TestPredictionModelUpdate:
    """PredictionModelUpdate schema 测试。"""

    def test_partial_update(self):
        result = PredictionModelUpdate(model_name="新名称")
        assert result.model_name == "新名称"
        assert result.api_endpoint is None
        assert result.is_active is None

    def test_invalid_timeout(self):
        with pytest.raises(ValidationError):
            PredictionModelUpdate(timeout_seconds=0)

    def test_update_is_active(self):
        result = PredictionModelUpdate(is_active=False)
        assert result.is_active is False


class TestPredictionModelRead:
    """PredictionModelRead schema 测试。"""

    def test_from_model_with_key(self):
        from unittest.mock import MagicMock

        model = MagicMock()
        model.id = "550e8400-e29b-41d4-a716-446655440000"
        model.station_id = "660e8400-e29b-41d4-a716-446655440000"
        model.model_name = "风电预测模型"
        model.model_type = "wind"
        model.api_endpoint = "https://api.example.com/predict"
        model.api_key_encrypted = b"encrypted_data"
        model.api_auth_type = "api_key"
        model.call_frequency_cron = "0 6,12 * * *"
        model.timeout_seconds = 30
        model.is_active = True
        model.status = "running"
        model.last_check_at = "2026-03-01T07:00:00+08:00"
        model.last_check_status = "success"
        model.last_check_error = None
        model.last_fetch_at = None
        model.last_fetch_status = None
        model.last_fetch_error = None
        model.created_at = "2026-03-01T00:00:00+08:00"
        model.updated_at = "2026-03-01T07:00:00+08:00"

        result = PredictionModelRead.from_model(model)
        assert result.api_key_display == "****"
        assert result.model_name == "风电预测模型"
        assert result.status == "running"

    def test_from_model_without_key(self):
        from unittest.mock import MagicMock

        model = MagicMock()
        model.id = "550e8400-e29b-41d4-a716-446655440000"
        model.station_id = "660e8400-e29b-41d4-a716-446655440000"
        model.model_name = "测试模型"
        model.model_type = "solar"
        model.api_endpoint = "https://api.example.com"
        model.api_key_encrypted = None
        model.api_auth_type = "none"
        model.call_frequency_cron = "0 6,12 * * *"
        model.timeout_seconds = 30
        model.is_active = True
        model.status = "disabled"
        model.last_check_at = None
        model.last_check_status = None
        model.last_check_error = None
        model.last_fetch_at = None
        model.last_fetch_status = None
        model.last_fetch_error = None
        model.created_at = "2026-03-01T00:00:00+08:00"
        model.updated_at = "2026-03-01T07:00:00+08:00"

        result = PredictionModelRead.from_model(model)
        assert result.api_key_display is None

    def test_api_key_not_exposed(self):
        """验证 Read schema 不包含原始 api_key 字段。"""
        fields = PredictionModelRead.model_fields
        assert "api_key" not in fields
        assert "api_key_encrypted" not in fields


class TestConnectionTestResult:
    """ConnectionTestResult schema 测试。"""

    def test_success_result(self):
        now = datetime.now(timezone.utc)
        result = ConnectionTestResult(
            success=True,
            latency_ms=45.2,
            tested_at=now,
        )
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        now = datetime.now(timezone.utc)
        result = ConnectionTestResult(
            success=False,
            latency_ms=5000.0,
            error_message="连接超时",
            tested_at=now,
        )
        assert result.success is False
        assert result.error_message == "连接超时"


class TestPredictionModelStatus:
    """PredictionModelStatus schema 测试。"""

    def test_status_running(self):
        result = PredictionModelStatus(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            model_name="风电预测模型",
            status="running",
            last_check_at="2026-03-01T07:00:00+08:00",
            last_check_error=None,
        )
        assert result.status == "running"
        assert result.station_name is None

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            PredictionModelStatus(
                model_id="550e8400-e29b-41d4-a716-446655440000",
                model_name="test",
                status="unknown",
                last_check_at=None,
                last_check_error=None,
            )


class TestPredictionModelListResponse:
    """PredictionModelListResponse 测试。"""

    def test_construction(self):
        response = PredictionModelListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
        )
        assert response.total == 0
        assert response.page_size == 20


class TestPowerPredictionRead:
    """PowerPredictionRead schema 测试。"""

    def test_valid_prediction(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        result = PowerPredictionRead(
            prediction_date="2026-03-06",
            period=1,
            predicted_power_kw=Decimal("1500.00"),
            confidence_upper_kw=Decimal("1650.00"),
            confidence_lower_kw=Decimal("1350.00"),
            source="api",
            fetched_at=datetime.now(timezone.utc),
        )
        assert result.period == 1
        assert result.predicted_power_kw == Decimal("1500.00")

    def test_invalid_period_too_low(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        with pytest.raises(ValidationError, match="1-96"):
            PowerPredictionRead(
                prediction_date="2026-03-06",
                period=0,
                predicted_power_kw=Decimal("1500.00"),
                confidence_upper_kw=Decimal("1650.00"),
                confidence_lower_kw=Decimal("1350.00"),
                source="api",
                fetched_at=datetime.now(timezone.utc),
            )

    def test_invalid_period_too_high(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        with pytest.raises(ValidationError, match="1-96"):
            PowerPredictionRead(
                prediction_date="2026-03-06",
                period=97,
                predicted_power_kw=Decimal("1500.00"),
                confidence_upper_kw=Decimal("1650.00"),
                confidence_lower_kw=Decimal("1350.00"),
                source="api",
                fetched_at=datetime.now(timezone.utc),
            )

    def test_negative_power_rejected(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        with pytest.raises(ValidationError, match="不能为负"):
            PowerPredictionRead(
                prediction_date="2026-03-06",
                period=1,
                predicted_power_kw=Decimal("-10.00"),
                confidence_upper_kw=Decimal("100.00"),
                confidence_lower_kw=Decimal("-20.00"),
                source="api",
                fetched_at=datetime.now(timezone.utc),
            )

    def test_confidence_upper_less_than_predicted_rejected(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        with pytest.raises(ValidationError, match="上限不能小于预测值"):
            PowerPredictionRead(
                prediction_date="2026-03-06",
                period=1,
                predicted_power_kw=Decimal("1500.00"),
                confidence_upper_kw=Decimal("1400.00"),
                confidence_lower_kw=Decimal("1300.00"),
                source="api",
                fetched_at=datetime.now(timezone.utc),
            )

    def test_confidence_lower_greater_than_predicted_rejected(self):
        from app.schemas.prediction import PowerPredictionRead
        from decimal import Decimal

        with pytest.raises(ValidationError, match="下限不能大于预测值"):
            PowerPredictionRead(
                prediction_date="2026-03-06",
                period=1,
                predicted_power_kw=Decimal("1500.00"),
                confidence_upper_kw=Decimal("1650.00"),
                confidence_lower_kw=Decimal("1600.00"),
                source="api",
                fetched_at=datetime.now(timezone.utc),
            )


class TestFetchResult:
    """FetchResult schema 测试。"""

    def test_success_result(self):
        from app.schemas.prediction import FetchResult

        result = FetchResult(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            model_name="风电预测模型",
            success=True,
            records_count=96,
            fetched_at=datetime.now(timezone.utc),
        )
        assert result.success is True
        assert result.records_count == 96
        assert result.error_message is None

    def test_failure_result(self):
        from app.schemas.prediction import FetchResult

        result = FetchResult(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            model_name="风电预测模型",
            success=False,
            records_count=0,
            error_message="API调用超时",
            fetched_at=datetime.now(timezone.utc),
        )
        assert result.success is False
        assert result.error_message == "API调用超时"
