"""数据导入 API 集成测试 — 电站出力/储能运行数据端点扩展。

验证新增的 import_type/ems_format 参数、output-records / storage-records 端点。
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


def _make_job(job_id=None, status="pending", import_type="trading_data"):
    job = MagicMock()
    job.id = job_id or _JOB_ID
    job.file_name = f"{job_id or _JOB_ID}/test.csv"
    job.original_file_name = "test.csv"
    job.file_size = 1024
    job.station_id = _STATION_ID
    job.import_type = import_type
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


def _make_output_record():
    record = MagicMock()
    record.id = uuid.uuid4()
    record.trading_date = "2026-03-01"
    record.period = 1
    record.station_id = _STATION_ID
    record.actual_output_kw = 1500.00
    record.import_job_id = _JOB_ID
    record.created_at = "2026-03-01T10:00:00+08:00"
    return record


def _make_storage_record():
    record = MagicMock()
    record.id = uuid.uuid4()
    record.trading_date = "2026-03-01"
    record.period = 1
    record.device_id = uuid.uuid4()
    record.soc = 0.85
    record.charge_power_kw = 100.00
    record.discharge_power_kw = 0.00
    record.cycle_count = 150
    record.import_job_id = _JOB_ID
    record.created_at = "2026-03-01T10:00:00+08:00"
    return record


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
    from app.api.v1.data_imports import _get_data_import_service
    app.dependency_overrides[_get_data_import_service] = lambda: mock_service


class TestUploadWithImportType:
    """POST /api/v1/data-imports/upload — import_type / ems_format 参数测试。"""

    @pytest.mark.asyncio
    async def test_upload_station_output_type(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.create_import_job.return_value = _make_job(
            status="pending", import_type="station_output",
        )
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/data-imports/upload",
            files={"file": ("output.csv", b"trading_date,period,actual_output_kw\n", "text/csv")},
            data={
                "station_id": str(_STATION_ID),
                "import_type": "station_output",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["import_type"] == "station_output"

    @pytest.mark.asyncio
    async def test_upload_storage_with_ems_format(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.create_import_job.return_value = _make_job(
            status="pending", import_type="storage_operation",
        )
        _override_service(mock_service)

        response = await api_client.post(
            "/api/v1/data-imports/upload",
            files={"file": ("storage.csv", b"trading_date,period,soc\n", "text/csv")},
            data={
                "station_id": str(_STATION_ID),
                "import_type": "storage_operation",
                "ems_format": "sungrow",
            },
        )

        assert response.status_code == 201
        # 验证 service 接收到了 ems_format 参数
        call_kwargs = mock_service.create_import_job.call_args
        assert call_kwargs.kwargs.get("import_type") == "storage_operation"
        assert call_kwargs.kwargs.get("ems_format") == "sungrow"


class TestListWithImportTypeFilter:
    """GET /api/v1/data-imports — import_type 过滤参数测试。"""

    @pytest.mark.asyncio
    async def test_list_with_import_type(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_import_jobs.return_value = (
            [_make_job(import_type="station_output")], 1,
        )
        _override_service(mock_service)

        response = await api_client.get(
            "/api/v1/data-imports?import_type=station_output",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["import_type"] == "station_output"

        # 验证 import_type 传递给 service
        call_kwargs = mock_service.list_import_jobs.call_args
        assert call_kwargs.kwargs.get("import_type") == "station_output"


class TestOutputRecordsEndpoint:
    """GET /api/v1/data-imports/{job_id}/output-records 测试。"""

    @pytest.mark.asyncio
    async def test_returns_output_records(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_output_records.return_value = ([_make_output_record()], 1)
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/data-imports/{_JOB_ID}/output-records",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["period"] == 1

    @pytest.mark.asyncio
    async def test_trader_access_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/data-imports/{_JOB_ID}/output-records",
        )

        assert response.status_code == 403
        mock_service.list_output_records.assert_not_called()

    @pytest.mark.asyncio
    async def test_pagination(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_output_records.return_value = ([], 0)
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/data-imports/{_JOB_ID}/output-records?page=2&page_size=10",
        )

        assert response.status_code == 200
        call_kwargs = mock_service.list_output_records.call_args
        assert call_kwargs.kwargs.get("page") == 2
        assert call_kwargs.kwargs.get("page_size") == 10


class TestStorageRecordsEndpoint:
    """GET /api/v1/data-imports/{job_id}/storage-records 测试。"""

    @pytest.mark.asyncio
    async def test_returns_storage_records(self, api_client):
        admin = _make_admin()
        _override_auth(admin)

        mock_service = AsyncMock()
        mock_service.list_storage_records.return_value = ([_make_storage_record()], 1)
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/data-imports/{_JOB_ID}/storage-records",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["cycle_count"] == 150

    @pytest.mark.asyncio
    async def test_trader_access_returns_403(self, api_client):
        trader = _make_trader()
        _override_auth(trader)

        mock_service = AsyncMock()
        _override_service(mock_service)

        response = await api_client.get(
            f"/api/v1/data-imports/{_JOB_ID}/storage-records",
        )

        assert response.status_code == 403
        mock_service.list_storage_records.assert_not_called()
