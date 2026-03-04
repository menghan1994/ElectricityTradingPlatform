"""DataImportService 出力/储能数据方法的单元测试。"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BusinessError
from app.services.data_import_service import DataImportService


def _make_admin(user_id=None):
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.username = "admin"
    user.role = "admin"
    return user


def _make_job(job_id=None, station_id=None, import_type="trading_data"):
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.station_id = station_id or uuid.uuid4()
    job.import_type = import_type
    job.total_records = 100
    job.success_records = 90
    job.failed_records = 10
    job.data_completeness = 90.00
    return job


@pytest.fixture
def mock_import_job_repo():
    return AsyncMock()


@pytest.fixture
def mock_trading_record_repo():
    return AsyncMock()


@pytest.fixture
def mock_anomaly_repo():
    return AsyncMock()


@pytest.fixture
def mock_station_repo():
    return AsyncMock()


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def mock_station_output_repo():
    return AsyncMock()


@pytest.fixture
def mock_storage_operation_repo():
    return AsyncMock()


@pytest.fixture
def mock_storage_device_repo():
    return AsyncMock()


@pytest.fixture
def service(
    mock_import_job_repo,
    mock_trading_record_repo,
    mock_anomaly_repo,
    mock_station_repo,
    mock_audit_service,
    mock_station_output_repo,
    mock_storage_operation_repo,
    mock_storage_device_repo,
):
    return DataImportService(
        mock_import_job_repo,
        mock_trading_record_repo,
        mock_anomaly_repo,
        mock_station_repo,
        mock_audit_service,
        station_output_repo=mock_station_output_repo,
        storage_operation_repo=mock_storage_operation_repo,
        storage_device_repo=mock_storage_device_repo,
    )


class TestListOutputRecords:
    """list_output_records 测试。"""

    @pytest.mark.asyncio
    async def test_success(self, service, mock_import_job_repo, mock_station_output_repo):
        job = _make_job(import_type="station_output")
        mock_import_job_repo.get_by_id.return_value = job
        mock_station_output_repo.list_by_job.return_value = ([MagicMock()], 1)

        records, total = await service.list_output_records(job.id)

        assert total == 1
        assert len(records) == 1
        mock_station_output_repo.list_by_job.assert_called_once_with(
            import_job_id=job.id, page=1, page_size=20,
        )

    @pytest.mark.asyncio
    async def test_wrong_import_type_rejected(self, service, mock_import_job_repo):
        job = _make_job(import_type="trading_data")
        mock_import_job_repo.get_by_id.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.list_output_records(job.id)

        assert exc_info.value.code == "INVALID_IMPORT_TYPE"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_job_not_found(self, service, mock_import_job_repo):
        mock_import_job_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.list_output_records(uuid.uuid4())

        assert exc_info.value.code == "IMPORT_JOB_NOT_FOUND"


class TestListStorageRecords:
    """list_storage_records 测试。"""

    @pytest.mark.asyncio
    async def test_success(self, service, mock_import_job_repo, mock_storage_operation_repo):
        job = _make_job(import_type="storage_operation")
        mock_import_job_repo.get_by_id.return_value = job
        mock_storage_operation_repo.list_by_job.return_value = ([MagicMock()], 1)

        records, total = await service.list_storage_records(job.id)

        assert total == 1
        mock_storage_operation_repo.list_by_job.assert_called_once_with(
            import_job_id=job.id, page=1, page_size=20,
        )

    @pytest.mark.asyncio
    async def test_wrong_import_type_rejected(self, service, mock_import_job_repo):
        job = _make_job(import_type="trading_data")
        mock_import_job_repo.get_by_id.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.list_storage_records(job.id)

        assert exc_info.value.code == "INVALID_IMPORT_TYPE"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_job_not_found(self, service, mock_import_job_repo):
        mock_import_job_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.list_storage_records(uuid.uuid4())

        assert exc_info.value.code == "IMPORT_JOB_NOT_FOUND"


class TestListImportJobsWithTypeFilter:
    """list_import_jobs import_type 过滤测试。"""

    @pytest.mark.asyncio
    async def test_passes_import_type_to_repo(self, service, mock_import_job_repo):
        mock_import_job_repo.list_all_paginated.return_value = ([], 0)

        await service.list_import_jobs(
            page=1, page_size=10, import_type="station_output",
        )

        call_kwargs = mock_import_job_repo.list_all_paginated.call_args.kwargs
        assert call_kwargs["import_type_filter"] == "station_output"

    @pytest.mark.asyncio
    async def test_none_import_type(self, service, mock_import_job_repo):
        mock_import_job_repo.list_all_paginated.return_value = ([], 0)

        await service.list_import_jobs()

        call_kwargs = mock_import_job_repo.list_all_paginated.call_args.kwargs
        assert call_kwargs["import_type_filter"] is None
