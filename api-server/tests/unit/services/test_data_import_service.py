import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BusinessError
from app.services.data_import_service import DataImportService


def _make_station(station_id=None, is_active=True):
    station = MagicMock()
    station.id = station_id or uuid.uuid4()
    station.name = "测试电站"
    station.province = "guangdong"
    station.is_active = is_active
    return station


def _make_admin(user_id=None):
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.username = "admin"
    user.role = "admin"
    return user


def _make_job(job_id=None, status="pending", station_id=None):
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.status = status
    job.station_id = station_id or uuid.uuid4()
    job.celery_task_id = "celery-task-123"
    job.last_processed_row = 500
    job.original_file_name = "test.csv"
    job.file_size = 1024
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
def service(
    mock_import_job_repo,
    mock_trading_record_repo,
    mock_anomaly_repo,
    mock_station_repo,
    mock_audit_service,
):
    return DataImportService(
        mock_import_job_repo,
        mock_trading_record_repo,
        mock_anomaly_repo,
        mock_station_repo,
        mock_audit_service,
    )


def _mock_station_query_result(station):
    """创建模拟的 session.execute() 返回值。"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = station
    return result


class TestCreateImportJob:
    """create_import_job 测试。"""

    @pytest.mark.asyncio
    async def test_station_not_found(self, service, mock_station_repo):
        mock_station_repo.session.execute.return_value = _mock_station_query_result(None)

        file = MagicMock()
        file.filename = "test.csv"
        file.read = AsyncMock(return_value=b"")

        with pytest.raises(BusinessError) as exc_info:
            await service.create_import_job(uuid.uuid4(), file, _make_admin())

        assert exc_info.value.code == "STATION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_station_inactive(self, service, mock_station_repo):
        mock_station_repo.session.execute.return_value = _mock_station_query_result(
            _make_station(is_active=False),
        )

        file = MagicMock()
        file.filename = "test.csv"
        file.read = AsyncMock(return_value=b"")

        with pytest.raises(BusinessError) as exc_info:
            await service.create_import_job(uuid.uuid4(), file, _make_admin())

        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_already_processing(self, service, mock_station_repo, mock_import_job_repo):
        station = _make_station()
        mock_station_repo.session.execute.return_value = _mock_station_query_result(station)
        mock_import_job_repo.has_processing_job.return_value = True

        file = MagicMock()
        file.filename = "test.csv"
        file.read = AsyncMock(return_value=b"")

        with pytest.raises(BusinessError) as exc_info:
            await service.create_import_job(station.id, file, _make_admin())

        assert exc_info.value.code == "IMPORT_ALREADY_PROCESSING"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    @patch("app.services.data_import_service.settings")
    async def test_create_success(
        self, mock_settings,
        service, mock_station_repo, mock_import_job_repo, mock_audit_service,
        tmp_path,
    ):
        station = _make_station()
        admin = _make_admin()
        mock_station_repo.session.execute.return_value = _mock_station_query_result(station)
        mock_import_job_repo.has_processing_job.return_value = False

        created_job = _make_job(station_id=station.id)
        mock_import_job_repo.create.return_value = created_job
        mock_import_job_repo.session = AsyncMock()

        mock_settings.DATA_IMPORT_DIR = str(tmp_path)
        mock_settings.MAX_IMPORT_FILE_SIZE = 100 * 1024 * 1024

        # Mock file with chunked read (streaming upload)
        file_data = b"trading_date,period,clearing_price\n2025-01-01,1,100.00"
        file = MagicMock()
        file.filename = "test.csv"
        file.read = AsyncMock(side_effect=[file_data, b""])

        with patch("app.tasks.import_tasks.process_trading_data_import") as mock_task:
            mock_task.delay.return_value = MagicMock(id="celery-task-abc")
            result = await service.create_import_job(station.id, file, admin, "127.0.0.1")

        assert result == created_job
        mock_import_job_repo.create.assert_called_once()
        mock_audit_service.log_action.assert_called_once()


class TestCancelImportJob:
    """cancel_import_job 测试。"""

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, service, mock_import_job_repo):
        mock_import_job_repo.get_by_id_for_update.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.cancel_import_job(uuid.uuid4(), _make_admin())

        assert exc_info.value.code == "IMPORT_JOB_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cancel_not_processing(self, service, mock_import_job_repo):
        job = _make_job(status="completed")
        mock_import_job_repo.get_by_id_for_update.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.cancel_import_job(job.id, _make_admin())

        assert exc_info.value.code == "IMPORT_CANNOT_CANCEL"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_pending_not_allowed(self, service, mock_import_job_repo):
        job = _make_job(status="pending")
        mock_import_job_repo.get_by_id_for_update.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.cancel_import_job(job.id, _make_admin())

        assert exc_info.value.code == "IMPORT_CANNOT_CANCEL"

    @pytest.mark.asyncio
    @patch("app.tasks.celery_app.celery_app")
    async def test_cancel_success(
        self, mock_celery_app, service, mock_import_job_repo, mock_audit_service,
    ):
        job = _make_job(status="processing")
        mock_import_job_repo.get_by_id_for_update.return_value = job
        admin = _make_admin()

        result = await service.cancel_import_job(job.id, admin, "127.0.0.1")

        assert job.status == "cancelled"
        mock_celery_app.control.revoke.assert_called_once_with(
            job.celery_task_id, terminate=True,
        )
        mock_audit_service.log_action.assert_called_once()
        assert result == job


class TestResumeImportJob:
    """resume_import_job 测试。"""

    @pytest.mark.asyncio
    async def test_resume_not_found(self, service, mock_import_job_repo):
        mock_import_job_repo.get_by_id_for_update.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.resume_import_job(uuid.uuid4(), _make_admin())

        assert exc_info.value.code == "IMPORT_JOB_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_resume_not_failed_or_cancelled(self, service, mock_import_job_repo):
        job = _make_job(status="processing")
        mock_import_job_repo.get_by_id_for_update.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.resume_import_job(job.id, _make_admin())

        assert exc_info.value.code == "IMPORT_CANNOT_RESUME"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_resume_completed_not_allowed(self, service, mock_import_job_repo):
        job = _make_job(status="completed")
        mock_import_job_repo.get_by_id_for_update.return_value = job

        with pytest.raises(BusinessError) as exc_info:
            await service.resume_import_job(job.id, _make_admin())

        assert exc_info.value.code == "IMPORT_CANNOT_RESUME"

    @pytest.mark.asyncio
    async def test_resume_from_failed_success(
        self, service, mock_import_job_repo, mock_audit_service,
    ):
        job = _make_job(status="failed")
        job.last_processed_row = 500
        mock_import_job_repo.get_by_id_for_update.return_value = job
        admin = _make_admin()

        with patch("app.tasks.import_tasks.process_trading_data_import") as mock_task:
            mock_task.delay.return_value = MagicMock(id="celery-resume-123")
            result = await service.resume_import_job(job.id, admin, "127.0.0.1")

        assert job.status == "processing"
        assert job.error_message is None
        mock_task.delay.assert_called_once_with(str(job.id), resume_from_row=500)
        mock_audit_service.log_action.assert_called_once()
        assert job.celery_task_id == "celery-resume-123"
        assert result == job

    @pytest.mark.asyncio
    async def test_resume_from_cancelled_success(
        self, service, mock_import_job_repo, mock_audit_service,
    ):
        job = _make_job(status="cancelled")
        job.last_processed_row = 200
        mock_import_job_repo.get_by_id_for_update.return_value = job
        admin = _make_admin()

        with patch("app.tasks.import_tasks.process_trading_data_import") as mock_task:
            mock_task.delay.return_value = MagicMock(id="celery-resume-456")
            result = await service.resume_import_job(job.id, admin)

        assert job.status == "processing"
        mock_task.delay.assert_called_once_with(str(job.id), resume_from_row=200)
        assert result == job


class TestGetImportResult:
    """get_import_result 测试。"""

    @pytest.mark.asyncio
    async def test_result_aggregation(self, service, mock_import_job_repo, mock_anomaly_repo):
        job = _make_job(status="completed")
        job.total_records = 1000
        job.success_records = 980
        job.failed_records = 20
        job.data_completeness = 98.00
        mock_import_job_repo.get_by_id.return_value = job

        mock_anomaly_repo.get_summary_by_job.return_value = [
            {"anomaly_type": "format_error", "count": 10},
            {"anomaly_type": "out_of_range", "count": 5},
            {"anomaly_type": "duplicate", "count": 5},
        ]

        result = await service.get_import_result(job.id)

        assert result["total_records"] == 1000
        assert result["success_records"] == 980
        assert result["failed_records"] == 20
        assert len(result["anomaly_summary"]) == 3
        assert result["anomaly_summary"][0]["anomaly_type"] == "format_error"
        assert result["anomaly_summary"][0]["count"] == 10
