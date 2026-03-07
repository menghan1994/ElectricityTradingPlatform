import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BusinessError
from app.services.prediction_adapters.base import PredictionRecord
from app.services.prediction_service import PredictionService, validate_prediction_records


def _make_model(
    model_name="风电预测模型",
    model_type="wind",
    api_endpoint="https://api.example.com/predict",
    api_key_encrypted=None,
    api_auth_type="api_key",
    timeout_seconds=30,
    is_active=True,
    status="disabled",
):
    model = MagicMock()
    model.id = uuid.uuid4()
    model.station_id = uuid.uuid4()
    model.model_name = model_name
    model.model_type = model_type
    model.api_endpoint = api_endpoint
    model.api_key_encrypted = api_key_encrypted
    model.api_auth_type = api_auth_type
    model.call_frequency_cron = "0 6,12 * * *"
    model.timeout_seconds = timeout_seconds
    model.is_active = is_active
    model.status = status
    model.last_check_at = None
    model.last_check_status = None
    model.last_check_error = None
    model.last_fetch_at = None
    model.last_fetch_status = None
    model.last_fetch_error = None
    model.created_at = "2026-03-01T00:00:00+08:00"
    model.updated_at = "2026-03-01T00:00:00+08:00"
    return model


@pytest.fixture
def mock_model_repo():
    return AsyncMock()


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def service(mock_model_repo, mock_audit_service):
    return PredictionService(mock_model_repo, mock_audit_service)


class TestCreateModel:
    """create_model 方法测试。"""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_model_repo):
        created_model = _make_model()
        mock_model_repo.create.return_value = created_model
        mock_model_repo.get_by_id.return_value = created_model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = True
            mock_get_adapter.return_value = mock_adapter

            result = await service.create_model(
                model_name="风电预测模型",
                model_type="wind",
                api_endpoint="https://api.example.com/predict",
                api_key=None,
                api_auth_type="api_key",
                call_frequency_cron="0 6,12 * * *",
                timeout_seconds=30,
                station_id=uuid.uuid4(),
            )
            assert result.model_name == "风电预测模型"
            mock_model_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_audit(self, service, mock_model_repo, mock_audit_service):
        created_model = _make_model()
        mock_model_repo.create.return_value = created_model
        mock_model_repo.get_by_id.return_value = created_model
        user_id = uuid.uuid4()

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = False
            mock_get_adapter.return_value = mock_adapter

            await service.create_model(
                model_name="测试模型",
                model_type="wind",
                api_endpoint="https://api.example.com",
                api_key=None,
                api_auth_type="api_key",
                call_frequency_cron="0 6 * * *",
                timeout_seconds=30,
                station_id=uuid.uuid4(),
                user_id=user_id,
            )
            mock_audit_service.log_action.assert_called_once()


class TestUpdateModel:
    """update_model 方法测试。"""

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model
        mock_model_repo.session = AsyncMock()

        result = await service.update_model(
            model.id,
            {"model_name": "新名称"},
        )
        assert result.model_name == "新名称"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_model_repo):
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.update_model(uuid.uuid4(), {"model_name": "test"})
        assert exc_info.value.code == "MODEL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_api_key(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model
        mock_model_repo.session = AsyncMock()

        with patch("app.services.prediction_service._encrypt_api_key") as mock_encrypt:
            mock_encrypt.return_value = b"encrypted"
            await service.update_model(
                model.id,
                {"api_key": "new-secret"},
            )
            mock_encrypt.assert_called_once_with("new-secret")


class TestDeleteModel:
    """delete_model 方法测试。"""

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model

        await service.delete_model(model.id)
        mock_model_repo.delete.assert_called_once_with(model)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_model_repo):
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.delete_model(uuid.uuid4())
        assert exc_info.value.code == "MODEL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_with_audit(self, service, mock_model_repo, mock_audit_service):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model
        user_id = uuid.uuid4()

        await service.delete_model(model.id, user_id=user_id)
        mock_audit_service.log_action.assert_called_once()


class TestGetModel:
    """get_model 方法测试。"""

    @pytest.mark.asyncio
    async def test_get_success(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model

        result = await service.get_model(model.id)
        assert result.model_name == "风电预测模型"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service, mock_model_repo):
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.get_model(uuid.uuid4())
        assert exc_info.value.code == "MODEL_NOT_FOUND"


class TestTestConnection:
    """test_connection 方法测试。"""

    @pytest.mark.asyncio
    async def test_connection_success(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = True
            mock_get_adapter.return_value = mock_adapter

            result = await service.test_connection(model.id)
            assert result.success is True
            assert result.latency_ms is not None
            mock_model_repo.update_check_result.assert_called()

    @pytest.mark.asyncio
    async def test_connection_failure(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = False
            mock_get_adapter.return_value = mock_adapter

            result = await service.test_connection(model.id)
            assert result.success is False
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_connection_exception(self, service, mock_model_repo):
        model = _make_model()
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.side_effect = RuntimeError("连接超时")
            mock_get_adapter.return_value = mock_adapter

            result = await service.test_connection(model.id)
            assert result.success is False
            assert "连接超时" in result.error_message

    @pytest.mark.asyncio
    async def test_connection_model_not_found(self, service, mock_model_repo):
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.test_connection(uuid.uuid4())
        assert exc_info.value.code == "MODEL_NOT_FOUND"


class TestCheckModelHealth:
    """check_model_health 方法测试。"""

    @pytest.mark.asyncio
    async def test_health_running(self, service, mock_model_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = True
            mock_get_adapter.return_value = mock_adapter

            result = await service.check_model_health(model.id)
            assert result == "running"

    @pytest.mark.asyncio
    async def test_health_error(self, service, mock_model_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.return_value = False
            mock_get_adapter.return_value = mock_adapter

            result = await service.check_model_health(model.id)
            assert result == "error"

    @pytest.mark.asyncio
    async def test_health_exception(self, service, mock_model_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.health_check.side_effect = Exception("网络异常")
            mock_get_adapter.return_value = mock_adapter

            result = await service.check_model_health(model.id)
            assert result == "error"
            mock_model_repo.update_check_result.assert_called()


class TestListModels:
    """list_models 方法测试。"""

    @pytest.mark.asyncio
    async def test_list_with_defaults(self, service, mock_model_repo):
        models_list = [_make_model(), _make_model(model_name="模型2")]
        mock_model_repo.list_all_paginated.return_value = (models_list, 2)

        result, total = await service.list_models()
        assert total == 2
        assert len(result) == 2
        mock_model_repo.list_all_paginated.assert_called_once_with(
            station_id=None, page=1, page_size=20,
        )


class TestGetAllModelStatuses:
    """get_all_model_statuses 方法测试。"""

    @pytest.mark.asyncio
    async def test_statuses_list(self, service, mock_model_repo):
        model1 = _make_model(status="running")
        model2 = _make_model(model_name="模型2", status="error")
        mock_model_repo.get_all_active_with_station_name.return_value = [
            (model1, "风电站A"),
            (model2, "光伏站B"),
        ]

        result = await service.get_all_model_statuses()
        assert len(result) == 2
        assert result[0].status == "running"
        assert result[0].station_name == "风电站A"
        assert result[1].status == "error"
        assert result[1].station_name == "光伏站B"

    @pytest.mark.asyncio
    async def test_no_active_models(self, service, mock_model_repo):
        mock_model_repo.get_all_active_with_station_name.return_value = []

        result = await service.get_all_model_statuses()
        assert len(result) == 0


class TestValidatePredictionRecords:
    """validate_prediction_records 测试。"""

    def _make_record(self, period=1, power=1500, upper=1650, lower=1350):
        return PredictionRecord(
            period=period,
            predicted_power_kw=Decimal(str(power)),
            confidence_upper_kw=Decimal(str(upper)),
            confidence_lower_kw=Decimal(str(lower)),
        )

    def test_all_valid_96_records(self):
        records = [self._make_record(period=i) for i in range(1, 97)]
        valid, errors = validate_prediction_records(records)
        assert len(valid) == 96
        assert len(errors) == 0

    def test_invalid_period(self):
        records = [self._make_record(period=0)]
        valid, errors = validate_prediction_records(records)
        assert len(valid) == 0
        assert any("Invalid period" in e for e in errors)

    def test_negative_power(self):
        records = [self._make_record(power=-10, upper=100, lower=-20)]
        valid, errors = validate_prediction_records(records)
        assert len(valid) == 0
        assert any("negative power" in e for e in errors)

    def test_confidence_violation(self):
        records = [self._make_record(power=1500, upper=1400, lower=1300)]
        valid, errors = validate_prediction_records(records)
        assert len(valid) == 0
        assert any("confidence violation" in e for e in errors)

    def test_incomplete_records(self):
        records = [self._make_record(period=i) for i in range(1, 50)]
        valid, errors = validate_prediction_records(records)
        assert len(valid) == 49
        assert any("Incomplete" in e for e in errors)


class TestFetchPredictions:
    """fetch_predictions 方法测试。"""

    @pytest.fixture
    def mock_prediction_repo(self):
        return AsyncMock()

    @pytest.fixture
    def fetch_service(self, mock_model_repo, mock_audit_service, mock_prediction_repo):
        return PredictionService(mock_model_repo, mock_audit_service, prediction_repo=mock_prediction_repo)

    @pytest.mark.asyncio
    async def test_fetch_success(self, fetch_service, mock_model_repo, mock_prediction_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model
        mock_model_repo.get_all_active_with_station_name.return_value = [(model, "风电站A")]
        mock_prediction_repo.bulk_upsert.return_value = 96

        records = [
            PredictionRecord(
                period=i,
                predicted_power_kw=Decimal("1500"),
                confidence_upper_kw=Decimal("1650"),
                confidence_lower_kw=Decimal("1350"),
            )
            for i in range(1, 97)
        ]

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.fetch_predictions.return_value = records
            mock_get_adapter.return_value = mock_adapter

            result = await fetch_service.fetch_predictions(
                model.id, date(2026, 3, 6),
            )
            assert result.success is True
            assert result.records_count == 96
            mock_model_repo.update_fetch_result.assert_called_once()
            mock_prediction_repo.bulk_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_api_failure(self, fetch_service, mock_model_repo, mock_prediction_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model
        mock_model_repo.get_all_active_with_station_name.return_value = [(model, "风电站A")]

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.fetch_predictions.side_effect = RuntimeError("API超时")
            mock_get_adapter.return_value = mock_adapter

            result = await fetch_service.fetch_predictions(
                model.id, date(2026, 3, 6),
            )
            assert result.success is False
            assert "API超时" in result.error_message
            mock_model_repo.update_fetch_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_quality_all_invalid(self, fetch_service, mock_model_repo, mock_prediction_repo):
        model = _make_model(status="running")
        mock_model_repo.get_by_id.return_value = model
        mock_model_repo.get_all_active_with_station_name.return_value = [(model, "风电站A")]

        # All records have invalid periods
        records = [
            PredictionRecord(
                period=0,
                predicted_power_kw=Decimal("1500"),
                confidence_upper_kw=Decimal("1650"),
                confidence_lower_kw=Decimal("1350"),
            )
        ]

        with patch("app.services.prediction_service.get_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.fetch_predictions.return_value = records
            mock_get_adapter.return_value = mock_adapter

            result = await fetch_service.fetch_predictions(
                model.id, date(2026, 3, 6),
            )
            assert result.success is False
            assert result.records_count == 0
            mock_prediction_repo.bulk_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_model_not_found(self, fetch_service, mock_model_repo):
        mock_model_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await fetch_service.fetch_predictions(uuid.uuid4(), date(2026, 3, 6))
        assert exc_info.value.code == "MODEL_NOT_FOUND"
