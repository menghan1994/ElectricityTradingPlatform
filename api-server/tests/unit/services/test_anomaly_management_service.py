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


def _make_anomaly(anomaly_id=None, status="pending", anomaly_type="format_error",
                  field_name="clearing_price", raw_value="abc", import_job_id=None):
    anomaly = MagicMock()
    anomaly.id = anomaly_id or uuid.uuid4()
    anomaly.import_job_id = import_job_id or uuid.uuid4()
    anomaly.row_number = 42
    anomaly.anomaly_type = anomaly_type
    anomaly.field_name = field_name
    anomaly.raw_value = raw_value
    anomaly.description = "测试异常"
    anomaly.status = status
    return anomaly


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


class TestCorrectAnomaly:
    """correct_anomaly 测试。"""

    @pytest.mark.asyncio
    async def test_correct_success_with_audit(
        self, service, mock_anomaly_repo, mock_import_job_repo,
        mock_trading_record_repo, mock_audit_service,
    ):
        anomaly = _make_anomaly(field_name="clearing_price", raw_value="abc")
        job = _make_job(job_id=anomaly.import_job_id)
        admin = _make_admin()

        mock_anomaly_repo.get_by_id_for_update.return_value = anomaly
        mock_anomaly_repo.get_by_id.return_value = anomaly
        mock_import_job_repo.get_by_id.return_value = job

        result = await service.correct_anomaly(
            anomaly.id, "350.00", admin, "127.0.0.1",
        )

        mock_anomaly_repo.update_anomaly_status.assert_called_once_with(
            anomaly.id, "corrected",
        )
        mock_audit_service.log_action.assert_called_once()
        assert result == anomaly

    @pytest.mark.asyncio
    async def test_correct_anomaly_not_found(self, service, mock_anomaly_repo):
        mock_anomaly_repo.get_by_id_for_update.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.correct_anomaly(uuid.uuid4(), "100", _make_admin())

        assert exc_info.value.code == "ANOMALY_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_correct_non_pending_rejected(self, service, mock_anomaly_repo):
        anomaly = _make_anomaly(status="corrected")
        mock_anomaly_repo.get_by_id_for_update.return_value = anomaly

        with pytest.raises(BusinessError) as exc_info:
            await service.correct_anomaly(anomaly.id, "100", _make_admin())

        assert exc_info.value.code == "ANOMALY_ALREADY_PROCESSED"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_correct_invalid_price_value(self, service, mock_anomaly_repo):
        anomaly = _make_anomaly(field_name="clearing_price")
        mock_anomaly_repo.get_by_id_for_update.return_value = anomaly

        with pytest.raises(BusinessError) as exc_info:
            await service.correct_anomaly(anomaly.id, "not_a_number", _make_admin())

        assert exc_info.value.code == "INVALID_CORRECTED_VALUE"
        assert exc_info.value.status_code == 422


class TestConfirmAnomalyNormal:
    """confirm_anomaly_normal 测试。"""

    @pytest.mark.asyncio
    async def test_confirm_success_with_audit(
        self, service, mock_anomaly_repo, mock_audit_service,
    ):
        anomaly = _make_anomaly(status="pending")
        admin = _make_admin()

        mock_anomaly_repo.get_by_id_for_update.return_value = anomaly
        mock_anomaly_repo.get_by_id.return_value = anomaly

        result = await service.confirm_anomaly_normal(anomaly.id, admin, "127.0.0.1")

        mock_anomaly_repo.update_anomaly_status.assert_called_once_with(
            anomaly.id, "confirmed_normal",
        )
        mock_audit_service.log_action.assert_called_once()
        assert result == anomaly

    @pytest.mark.asyncio
    async def test_confirm_non_pending_rejected(self, service, mock_anomaly_repo):
        anomaly = _make_anomaly(status="deleted")
        mock_anomaly_repo.get_by_id_for_update.return_value = anomaly

        with pytest.raises(BusinessError) as exc_info:
            await service.confirm_anomaly_normal(anomaly.id, _make_admin())

        assert exc_info.value.code == "ANOMALY_ALREADY_PROCESSED"


class TestBulkDeleteAnomalies:
    """bulk_delete_anomalies 测试。"""

    @pytest.mark.asyncio
    async def test_bulk_delete_success(
        self, service, mock_anomaly_repo, mock_audit_service,
    ):
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        anomaly1 = _make_anomaly(anomaly_id=id1, status="pending")
        anomaly2 = _make_anomaly(anomaly_id=id2, status="pending")
        admin = _make_admin()

        mock_anomaly_repo.get_by_ids.return_value = [anomaly1, anomaly2]
        mock_anomaly_repo.bulk_update_status.return_value = 2

        result = await service.bulk_delete_anomalies([id1, id2], admin, "127.0.0.1")

        assert result == 2
        mock_anomaly_repo.bulk_update_status.assert_called_once_with([id1, id2], "deleted")
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_delete_non_pending_rejected(self, service, mock_anomaly_repo):
        id1 = uuid.uuid4()
        anomaly = _make_anomaly(anomaly_id=id1, status="corrected")
        mock_anomaly_repo.get_by_ids.return_value = [anomaly]

        with pytest.raises(BusinessError) as exc_info:
            await service.bulk_delete_anomalies([id1], _make_admin())

        assert exc_info.value.code == "BULK_PARTIAL_FAILURE"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_bulk_delete_not_found(self, service, mock_anomaly_repo):
        mock_anomaly_repo.get_by_ids.return_value = []

        with pytest.raises(BusinessError) as exc_info:
            await service.bulk_delete_anomalies([uuid.uuid4()], _make_admin())

        assert exc_info.value.code == "ANOMALY_NOT_FOUND"


class TestBulkConfirmNormal:
    """bulk_confirm_normal 测试。"""

    @pytest.mark.asyncio
    async def test_bulk_confirm_success(
        self, service, mock_anomaly_repo, mock_audit_service,
    ):
        id1 = uuid.uuid4()
        anomaly1 = _make_anomaly(anomaly_id=id1, status="pending")
        admin = _make_admin()

        mock_anomaly_repo.get_by_ids.return_value = [anomaly1]
        mock_anomaly_repo.bulk_update_status.return_value = 1

        result = await service.bulk_confirm_normal([id1], admin, "127.0.0.1")

        assert result == 1
        mock_anomaly_repo.bulk_update_status.assert_called_once_with([id1], "confirmed_normal")
        mock_audit_service.log_action.assert_called_once()


class TestGetAnomalyDetail:
    """get_anomaly_detail 测试。"""

    @pytest.mark.asyncio
    async def test_returns_anomaly_with_job_info(
        self, service, mock_anomaly_repo, mock_import_job_repo,
    ):
        anomaly = _make_anomaly()
        job = _make_job(job_id=anomaly.import_job_id)
        job.original_file_name = "test.csv"

        mock_anomaly_repo.get_by_id.return_value = anomaly
        mock_import_job_repo.get_by_id.return_value = job

        result = await service.get_anomaly_detail(anomaly.id)

        assert result["anomaly"] == anomaly
        assert result["original_file_name"] == "test.csv"
        assert result["station_id"] == job.station_id

    @pytest.mark.asyncio
    async def test_not_found_raises(self, service, mock_anomaly_repo):
        mock_anomaly_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await service.get_anomaly_detail(uuid.uuid4())

        assert exc_info.value.code == "ANOMALY_NOT_FOUND"


class TestGetAnomalySummary:
    """get_anomaly_summary 测试。"""

    @pytest.mark.asyncio
    async def test_passes_filters_to_repo(self, service, mock_anomaly_repo):
        mock_anomaly_repo.get_summary_all.return_value = [
            {"anomaly_type": "format_error", "count": 5},
        ]
        job_id = uuid.uuid4()

        result = await service.get_anomaly_summary(
            import_job_id=job_id, status="pending",
        )

        assert len(result) == 1
        mock_anomaly_repo.get_summary_all.assert_called_once_with(
            import_job_id_filter=job_id, status_filter="pending",
        )


class TestListAnomaliesGlobal:
    """list_anomalies_global 测试。"""

    @pytest.mark.asyncio
    async def test_list_passes_filters(self, service, mock_anomaly_repo):
        mock_anomaly_repo.list_all_anomalies.return_value = ([], 0)

        await service.list_anomalies_global(
            page=2, page_size=10,
            anomaly_type="missing", status="pending",
            import_job_id=uuid.uuid4(),
        )

        mock_anomaly_repo.list_all_anomalies.assert_called_once()
        call_kwargs = mock_anomaly_repo.list_all_anomalies.call_args
        assert call_kwargs.kwargs["page"] == 2
        assert call_kwargs.kwargs["page_size"] == 10
        assert call_kwargs.kwargs["anomaly_type_filter"] == "missing"
        assert call_kwargs.kwargs["status_filter"] == "pending"
