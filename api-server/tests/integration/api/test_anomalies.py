"""异常管理 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


_ADMIN_USER_ID = uuid.uuid4()
_ANOMALY_ID = uuid.uuid4()
_JOB_ID = uuid.uuid4()
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
    user.id = uuid.uuid4()
    user.username = "trader"
    user.role = "trader"
    user.is_active = True
    user.is_locked = False
    return user


def _make_anomaly(anomaly_id=None, status="pending"):
    anomaly = MagicMock()
    anomaly.id = anomaly_id or _ANOMALY_ID
    anomaly.import_job_id = _JOB_ID
    anomaly.row_number = 15
    anomaly.anomaly_type = "format_error"
    anomaly.field_name = "clearing_price"
    anomaly.raw_value = "abc"
    anomaly.description = "价格格式错误"
    anomaly.status = status
    anomaly.created_at = "2026-03-01T10:00:00+08:00"
    anomaly.updated_at = "2026-03-01T10:00:00+08:00"
    # AnomalyDetailRead 继承字段，需设为 None 避免 model_validate 读到 MagicMock
    anomaly.original_file_name = None
    anomaly.station_id = None
    return anomaly


def _make_job():
    job = MagicMock()
    job.id = _JOB_ID
    job.original_file_name = "test.csv"
    job.station_id = _STATION_ID
    return job


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
    from app.api.v1.anomalies import _get_data_import_service
    app.dependency_overrides[_get_data_import_service] = lambda: mock_service


class TestListAnomaliesEndpoint:
    """GET /api/v1/anomalies 测试。"""

    @pytest.mark.asyncio
    async def test_list_returns_paginated(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_anomalies_global.return_value = ([_make_anomaly()], 1)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["anomaly_type"] == "format_error"

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_anomalies_global.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies?anomaly_type=missing")

        assert response.status_code == 200
        mock_service.list_anomalies_global.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_with_job_filter(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_anomalies_global.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get(f"/api/v1/anomalies?import_job_id={_JOB_ID}")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_anomalies_global.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies?status=pending")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trader_list_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies")

        assert response.status_code == 403
        mock_service.list_anomalies_global.assert_not_called()


class TestGetAnomalyEndpoint:
    """GET /api/v1/anomalies/{anomaly_id} 测试。"""

    @pytest.mark.asyncio
    async def test_get_anomaly_returns_detail(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        anomaly = _make_anomaly()
        mock_service = AsyncMock()
        mock_service.get_anomaly_detail.return_value = {
            "anomaly": anomaly,
            "original_file_name": "test.csv",
            "station_id": _STATION_ID,
        }
        _override_service(mock_service)

        response = await api_client.get(f"/api/v1/anomalies/{_ANOMALY_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(_ANOMALY_ID)
        assert data["original_file_name"] == "test.csv"
        assert data["station_id"] == str(_STATION_ID)

    @pytest.mark.asyncio
    async def test_trader_get_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get(f"/api/v1/anomalies/{_ANOMALY_ID}")

        assert response.status_code == 403


class TestAnomalySummaryEndpoint:
    """GET /api/v1/anomalies/summary 测试。"""

    @pytest.mark.asyncio
    async def test_summary_returns_list(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.get_anomaly_summary.return_value = [
            {"anomaly_type": "format_error", "count": 5},
            {"anomaly_type": "missing", "count": 3},
        ]
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies/summary")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["anomaly_type"] == "format_error"
        assert data[0]["count"] == 5

    @pytest.mark.asyncio
    async def test_summary_with_job_filter(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.get_anomaly_summary.return_value = []
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/anomalies/summary?import_job_id={_JOB_ID}",
        )

        assert response.status_code == 200
        mock_service.get_anomaly_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_trader_summary_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/anomalies/summary")

        assert response.status_code == 403


class TestCorrectAnomalyEndpoint:
    """PATCH /api/v1/anomalies/{anomaly_id}/correct 测试。"""

    @pytest.mark.asyncio
    async def test_correct_returns_200(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.correct_anomaly.return_value = _make_anomaly(status="corrected")
        _override_service(mock_service)

        response = await api_client.patch(
            f"/api/v1/anomalies/{_ANOMALY_ID}/correct",
            json={"corrected_value": "350.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "corrected"

    @pytest.mark.asyncio
    async def test_trader_correct_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.patch(
            f"/api/v1/anomalies/{_ANOMALY_ID}/correct",
            json={"corrected_value": "350.00"},
        )

        assert response.status_code == 403


class TestConfirmNormalEndpoint:
    """PATCH /api/v1/anomalies/{anomaly_id}/confirm-normal 测试。"""

    @pytest.mark.asyncio
    async def test_confirm_returns_200(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.confirm_anomaly_normal.return_value = _make_anomaly(status="confirmed_normal")
        _override_service(mock_service)

        response = await api_client.patch(
            f"/api/v1/anomalies/{_ANOMALY_ID}/confirm-normal",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed_normal"

    @pytest.mark.asyncio
    async def test_trader_confirm_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.patch(
            f"/api/v1/anomalies/{_ANOMALY_ID}/confirm-normal",
        )

        assert response.status_code == 403


class TestBulkActionEndpoint:
    """POST /api/v1/anomalies/bulk-action 测试。"""

    @pytest.mark.asyncio
    async def test_bulk_delete_returns_affected_count(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.bulk_delete_anomalies.return_value = 3
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/anomalies/bulk-action",
            json={
                "anomaly_ids": [str(uuid.uuid4()) for _ in range(3)],
                "action": "delete",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["affected_count"] == 3
        assert data["action"] == "delete"

    @pytest.mark.asyncio
    async def test_bulk_confirm_normal_returns_affected_count(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.bulk_confirm_normal.return_value = 2
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/anomalies/bulk-action",
            json={
                "anomaly_ids": [str(uuid.uuid4()) for _ in range(2)],
                "action": "confirm_normal",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["affected_count"] == 2
        assert data["action"] == "confirm_normal"

    @pytest.mark.asyncio
    async def test_trader_bulk_action_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/anomalies/bulk-action",
            json={
                "anomaly_ids": [str(uuid.uuid4())],
                "action": "delete",
            },
        )

        assert response.status_code == 403
        mock_service.bulk_delete_anomalies.assert_not_called()
