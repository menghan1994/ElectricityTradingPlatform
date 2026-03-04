"""数据导入 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。

注意：Service 层通过 mock 注入。该模式与项目其他 API 集成测试一致
（如 test_market_rules.py, test_stations.py 等）。
真实 Service→Repository→DB 端到端测试需要 PostgreSQL + TimescaleDB
数据库 fixture，待测试基础设施完善后补充。
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


_ADMIN_USER_ID = uuid.uuid4()
_STATION_ID = uuid.uuid4()
_JOB_ID = uuid.uuid4()


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


def _make_job(job_id=None, status="pending"):
    job = MagicMock()
    job.id = job_id or _JOB_ID
    job.file_name = f"{job_id or _JOB_ID}/test.csv"
    job.original_file_name = "test.csv"
    job.file_size = 1024
    job.station_id = _STATION_ID
    job.import_type = "trading_data"
    job.ems_format = None
    job.status = status
    job.total_records = 100
    job.processed_records = 100
    job.success_records = 95
    job.failed_records = 5
    job.data_completeness = 95.00
    job.last_processed_row = 100
    job.celery_task_id = "celery-123"
    job.error_message = None
    job.started_at = "2026-03-01T10:00:00+08:00"
    job.completed_at = "2026-03-01T10:05:00+08:00"
    job.imported_by = _ADMIN_USER_ID
    job.created_at = "2026-03-01T09:59:50+08:00"
    job.updated_at = "2026-03-01T10:05:00+08:00"
    return job


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _override_auth(user):
    """覆盖认证依赖，返回指定用户。"""
    from app.core.dependencies import get_current_active_user

    app.dependency_overrides[get_current_active_user] = lambda: user


def _override_service(mock_service):
    """覆盖 DataImportService 依赖。"""
    from app.api.v1.data_imports import _get_data_import_service
    app.dependency_overrides[_get_data_import_service] = lambda: mock_service


class TestUploadEndpoint:
    """POST /api/v1/data-imports/upload 测试。"""

    @pytest.mark.asyncio
    async def test_admin_upload_csv_returns_201(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.create_import_job.return_value = _make_job(status="pending")
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/data-imports/upload",
            files={"file": ("test.csv", b"trading_date,period,clearing_price\n", "text/csv")},
            data={"station_id": str(_STATION_ID)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["original_file_name"] == "test.csv"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_trader_upload_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/data-imports/upload",
            files={"file": ("test.csv", b"trading_date,period,clearing_price\n", "text/csv")},
            data={"station_id": str(_STATION_ID)},
        )

        assert response.status_code == 403
        mock_service.create_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/data-imports/upload",
            files={"file": ("test.txt", b"some text", "text/plain")},
            data={"station_id": str(_STATION_ID)},
        )

        assert response.status_code == 422


class TestListEndpoint:
    """GET /api/v1/data-imports 测试。"""

    @pytest.mark.asyncio
    async def test_trader_list_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get("/api/v1/data-imports")

        assert response.status_code == 403
        mock_service.list_import_jobs.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_returns_paginated(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_import_jobs.return_value = ([_make_job()], 1)
        _override_service(mock_service)

        response = await api_client.get("/api/v1/data-imports")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1


class TestGetJobEndpoint:
    """GET /api/v1/data-imports/{job_id} 测试。"""

    @pytest.mark.asyncio
    async def test_get_job_detail(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.get_import_job.return_value = _make_job(status="completed")
        _override_service(mock_service)

        response = await api_client.get(f"/api/v1/data-imports/{_JOB_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestCancelEndpoint:
    """POST /api/v1/data-imports/{job_id}/cancel 测试。"""

    @pytest.mark.asyncio
    async def test_trader_cancel_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(f"/api/v1/data-imports/{_JOB_ID}/cancel")

        assert response.status_code == 403
        mock_service.cancel_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_updates_status(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.cancel_import_job.return_value = _make_job(status="cancelled")
        _override_service(mock_service)

        response = await api_client.post(f"/api/v1/data-imports/{_JOB_ID}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestResumeEndpoint:
    """POST /api/v1/data-imports/{job_id}/resume 测试。"""

    @pytest.mark.asyncio
    async def test_trader_resume_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.post(f"/api/v1/data-imports/{_JOB_ID}/resume")

        assert response.status_code == 403
        mock_service.resume_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_triggers_task(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.resume_import_job.return_value = _make_job(status="processing")
        _override_service(mock_service)

        response = await api_client.post(f"/api/v1/data-imports/{_JOB_ID}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
