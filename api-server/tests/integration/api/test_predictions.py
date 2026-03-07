"""预测模型管理 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

_ADMIN_USER_ID = uuid.uuid4()
_TRADER_USER_ID = uuid.uuid4()
_MODEL_ID = uuid.uuid4()
_STATION_ID = uuid.uuid4()


def _make_admin():
    user = MagicMock()
    user.id = _ADMIN_USER_ID
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    user.is_locked = False
    return user


def _make_trader():
    user = MagicMock()
    user.id = _TRADER_USER_ID
    user.username = "trader"
    user.role = "trader"
    user.is_active = True
    user.is_locked = False
    return user


def _make_operator():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "operator"
    user.role = "operator"
    user.is_active = True
    user.is_locked = False
    return user


def _make_model():
    model = MagicMock()
    model.id = _MODEL_ID
    model.station_id = _STATION_ID
    model.model_name = "风电预测模型"
    model.model_type = "wind"
    model.api_endpoint = "https://api.example.com/predict"
    model.api_key_encrypted = b"encrypted"
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
    return model


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _override_auth(user):
    from app.core.dependencies import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: user


def _override_service(mock_service):
    from app.api.v1.predictions import _get_prediction_service
    app.dependency_overrides[_get_prediction_service] = lambda: mock_service


class TestListPredictionModels:
    """GET /api/v1/prediction-models 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_list(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        mock_service.list_models.return_value = ([_make_model()], 1)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["model_name"] == "风电预测模型"
        assert data["items"][0]["api_key_display"] == "****"

    @pytest.mark.asyncio
    async def test_trader_can_list(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        mock_service.list_models.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_forbidden(self, api_client):
        _override_auth(_make_operator())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_filter_by_station_id(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        mock_service.list_models.return_value = ([_make_model()], 1)
        _override_service(mock_service)

        response = await api_client.get(
            "/api/v1/prediction-models",
            params={"station_id": str(_STATION_ID)},
        )
        assert response.status_code == 200
        mock_service.list_models.assert_called_once_with(
            station_id=_STATION_ID, page=1, page_size=20,
        )


class TestCreatePredictionModel:
    """POST /api/v1/prediction-models 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_create(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        mock_service.create_model.return_value = _make_model()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/prediction-models",
            json={
                "model_name": "风电预测模型",
                "model_type": "wind",
                "api_endpoint": "https://api.example.com/predict",
                "station_id": str(_STATION_ID),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == "风电预测模型"

    @pytest.mark.asyncio
    async def test_trader_cannot_create(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/prediction-models",
            json={
                "model_name": "test",
                "api_endpoint": "https://api.example.com",
                "station_id": str(_STATION_ID),
            },
        )
        assert response.status_code == 403


class TestUpdatePredictionModel:
    """PUT /api/v1/prediction-models/{id} 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_update(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        updated_model = _make_model()
        updated_model.model_name = "更新后的模型"
        mock_service.update_model.return_value = updated_model
        _override_service(mock_service)

        response = await api_client.put(
            f"/api/v1/prediction-models/{_MODEL_ID}",
            json={"model_name": "更新后的模型"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trader_cannot_update(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.put(
            f"/api/v1/prediction-models/{_MODEL_ID}",
            json={"model_name": "test"},
        )
        assert response.status_code == 403


class TestDeletePredictionModel:
    """DELETE /api/v1/prediction-models/{id} 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_delete(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.delete(f"/api/v1/prediction-models/{_MODEL_ID}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_trader_cannot_delete(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.delete(f"/api/v1/prediction-models/{_MODEL_ID}")
        assert response.status_code == 403


class TestTestConnection:
    """POST /api/v1/prediction-models/{id}/test-connection 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_test_connection(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        from app.schemas.prediction import ConnectionTestResult
        mock_service.test_connection.return_value = ConnectionTestResult(
            success=True,
            latency_ms=45.2,
            tested_at=datetime.now(timezone.utc),
        )
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/test-connection",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["latency_ms"] == 45.2

    @pytest.mark.asyncio
    async def test_trader_cannot_test_connection(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/test-connection",
        )
        assert response.status_code == 403


class TestModelStatuses:
    """GET /api/v1/prediction-models/status 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_view_statuses(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        from app.schemas.prediction import PredictionModelStatus
        mock_service.get_all_model_statuses.return_value = [
            PredictionModelStatus(
                model_id=str(_MODEL_ID),
                model_name="风电预测模型",
                status="running",
                last_check_at="2026-03-01T07:00:00+08:00",
                last_check_error=None,
            ),
        ]
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models/status")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "running"

    @pytest.mark.asyncio
    async def test_trader_can_view_statuses(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        mock_service.get_all_model_statuses.return_value = []
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_cannot_view_statuses(self, api_client):
        _override_auth(_make_operator())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/prediction-models/status")
        assert response.status_code == 403


class TestTriggerFetch:
    """POST /api/v1/prediction-models/{id}/fetch 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_trigger_fetch(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        from app.schemas.prediction import FetchResult
        mock_service.fetch_predictions.return_value = FetchResult(
            model_id=str(_MODEL_ID),
            model_name="风电预测模型",
            success=True,
            records_count=96,
            fetched_at=datetime.now(timezone.utc),
        )
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/fetch",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["records_count"] == 96

    @pytest.mark.asyncio
    async def test_fetch_with_custom_date(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        from app.schemas.prediction import FetchResult
        mock_service.fetch_predictions.return_value = FetchResult(
            model_id=str(_MODEL_ID),
            model_name="风电预测模型",
            success=True,
            records_count=96,
            fetched_at=datetime.now(timezone.utc),
        )
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/fetch",
            json={"prediction_date": "2026-03-10"},
        )
        assert response.status_code == 200
        mock_service.fetch_predictions.assert_called_once()
        call_kwargs = mock_service.fetch_predictions.call_args
        assert call_kwargs.kwargs["prediction_date"] == date(2026, 3, 10)

    @pytest.mark.asyncio
    async def test_trader_cannot_trigger_fetch(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/fetch",
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_fetch_failure_result(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        from app.schemas.prediction import FetchResult
        mock_service.fetch_predictions.return_value = FetchResult(
            model_id=str(_MODEL_ID),
            model_name="风电预测模型",
            success=False,
            records_count=0,
            error_message="API调用超时",
            fetched_at=datetime.now(timezone.utc),
        )
        _override_service(mock_service)

        response = await api_client.post(
            f"/api/v1/prediction-models/{_MODEL_ID}/fetch",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error_message"] == "API调用超时"


class TestGetModelPredictions:
    """GET /api/v1/prediction-models/{id}/predictions 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_query_predictions(self, api_client):
        _override_auth(_make_admin())
        mock_service = AsyncMock()
        mock_service.get_model.return_value = _make_model()
        _override_service(mock_service)

        # Override prediction_repo
        from app.api.v1.predictions import _get_prediction_repo
        mock_repo = AsyncMock()
        mock_prediction = MagicMock()
        mock_prediction.prediction_date = date(2026, 3, 6)
        mock_prediction.period = 1
        mock_prediction.predicted_power_kw = Decimal("1500.00")
        mock_prediction.confidence_upper_kw = Decimal("1650.00")
        mock_prediction.confidence_lower_kw = Decimal("1350.00")
        mock_prediction.source = "api"
        mock_prediction.fetched_at = datetime.now(timezone.utc)

        mock_repo.get_by_station_date_model.return_value = [mock_prediction]
        app.dependency_overrides[_get_prediction_repo] = lambda: mock_repo

        response = await api_client.get(
            f"/api/v1/prediction-models/{_MODEL_ID}/predictions",
            params={"prediction_date": "2026-03-06"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["period"] == 1

    @pytest.mark.asyncio
    async def test_trader_can_query_predictions(self, api_client):
        _override_auth(_make_trader())
        mock_service = AsyncMock()
        mock_service.get_model.return_value = _make_model()
        _override_service(mock_service)

        from app.api.v1.predictions import _get_prediction_repo
        mock_repo = AsyncMock()
        mock_repo.get_by_station_date_model.return_value = []
        app.dependency_overrides[_get_prediction_repo] = lambda: mock_repo

        response = await api_client.get(
            f"/api/v1/prediction-models/{_MODEL_ID}/predictions",
            params={"prediction_date": "2026-03-06"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_cannot_query_predictions(self, api_client):
        _override_auth(_make_operator())
        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/prediction-models/{_MODEL_ID}/predictions",
            params={"prediction_date": "2026-03-06"},
        )
        assert response.status_code == 403


class TestGetStationPredictions:
    """GET /api/v1/stations/{station_id}/predictions 测试。"""

    @pytest.mark.asyncio
    async def test_admin_can_query_station_predictions(self, api_client):
        _override_auth(_make_admin())

        from app.api.v1.stations import PowerPredictionRepository
        mock_repo = AsyncMock(spec=PowerPredictionRepository)
        mock_prediction = MagicMock()
        mock_prediction.prediction_date = date(2026, 3, 6)
        mock_prediction.period = 1
        mock_prediction.predicted_power_kw = Decimal("1500.00")
        mock_prediction.confidence_upper_kw = Decimal("1650.00")
        mock_prediction.confidence_lower_kw = Decimal("1350.00")
        mock_prediction.source = "api"
        mock_prediction.fetched_at = datetime.now(timezone.utc)

        mock_repo.get_by_station_date_model.return_value = [mock_prediction]

        # Override session to return our mock repo
        from app.core.database import get_db_session
        mock_session = AsyncMock()
        app.dependency_overrides[get_db_session] = lambda: mock_session

        # We need to patch the repo construction in the endpoint
        import app.api.v1.stations as stations_module
        original_repo_class = stations_module.PowerPredictionRepository
        stations_module.PowerPredictionRepository = lambda session: mock_repo

        try:
            response = await api_client.get(
                f"/api/v1/stations/{_STATION_ID}/predictions",
                params={"prediction_date": "2026-03-06"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["period"] == 1
        finally:
            stations_module.PowerPredictionRepository = original_repo_class

    @pytest.mark.asyncio
    async def test_operator_cannot_query_station_predictions(self, api_client):
        _override_auth(_make_operator())

        response = await api_client.get(
            f"/api/v1/stations/{_STATION_ID}/predictions",
            params={"prediction_date": "2026-03-06"},
        )
        assert response.status_code == 403
