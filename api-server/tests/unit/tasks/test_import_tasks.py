import csv
import tempfile
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.import_tasks import (
    BATCH_SIZE,
    COLUMN_MAPPING,
    ImportContext,
    PERIODS_PER_DAY,
    _detect_csv_encoding,
    _execute_import,
    _map_columns,
    _parse_date,
    _parse_output_kw,
    _parse_period,
    _parse_price,
)


class TestParseDate:
    """日期解析测试。"""

    def test_standard_format(self):
        assert _parse_date("2025-06-15") == date(2025, 6, 15)

    def test_slash_format(self):
        assert _parse_date("2025/06/15") == date(2025, 6, 15)

    def test_compact_format(self):
        assert _parse_date("20250615") == date(2025, 6, 15)

    def test_with_spaces(self):
        assert _parse_date("  2025-06-15  ") == date(2025, 6, 15)

    def test_invalid_date(self):
        assert _parse_date("not-a-date") is None

    def test_empty_string(self):
        assert _parse_date("") is None


class TestParsePeriod:
    """时段解析测试。"""

    def test_valid_period(self):
        assert _parse_period("48") == 48

    def test_period_min(self):
        assert _parse_period("1") == 1

    def test_period_max(self):
        assert _parse_period("96") == 96

    def test_period_zero(self):
        assert _parse_period("0") is None

    def test_period_97(self):
        assert _parse_period("97") is None

    def test_period_negative(self):
        assert _parse_period("-1") is None

    def test_period_non_numeric(self):
        assert _parse_period("abc") is None

    def test_period_float(self):
        assert _parse_period("48.5") is None


class TestParsePrice:
    """价格解析测试。"""

    def test_valid_price(self):
        assert _parse_price("350.50") == Decimal("350.50")

    def test_negative_price(self):
        assert _parse_price("-50.00") == Decimal("-50.00")

    def test_zero_price(self):
        assert _parse_price("0.00") == Decimal("0.00")

    def test_nan_price(self):
        assert _parse_price("NaN") is None

    def test_inf_price(self):
        assert _parse_price("Infinity") is None

    def test_negative_inf_price(self):
        assert _parse_price("-Infinity") is None

    def test_non_numeric(self):
        assert _parse_price("abc") is None

    def test_empty_string(self):
        assert _parse_price("") is None


class TestParseOutputKw:
    """出力解析测试。"""

    def test_valid_output(self):
        assert _parse_output_kw("500.50") == Decimal("500.50")

    def test_zero_output(self):
        assert _parse_output_kw("0") == Decimal("0")

    def test_negative_output(self):
        assert _parse_output_kw("-10.0") is None

    def test_invalid_output(self):
        assert _parse_output_kw("abc") is None

    def test_nan_output(self):
        assert _parse_output_kw("NaN") is None


class TestMapColumns:
    """列头映射测试。"""

    def test_english_columns(self):
        result = _map_columns(
            ["trading_date", "period", "clearing_price"],
            COLUMN_MAPPING,
            {"trading_date", "period", "clearing_price"},
        )
        assert result is not None
        assert result[0] == "trading_date"
        assert result[1] == "period"
        assert result[2] == "clearing_price"

    def test_chinese_columns(self):
        result = _map_columns(
            ["交易日期", "时段", "出清价格"],
            COLUMN_MAPPING,
            {"trading_date", "period", "clearing_price"},
        )
        assert result is not None
        assert result[0] == "trading_date"
        assert result[1] == "period"
        assert result[2] == "clearing_price"

    def test_mixed_case(self):
        result = _map_columns(
            ["Trading_Date", "Period", "Clearing_Price"],
            COLUMN_MAPPING,
            {"trading_date", "period", "clearing_price"},
        )
        assert result is not None

    def test_missing_column(self):
        result = _map_columns(
            ["trading_date", "period"],
            COLUMN_MAPPING,
            {"trading_date", "period", "clearing_price"},
        )
        assert result is None

    def test_extra_columns_ignored(self):
        result = _map_columns(
            ["trading_date", "extra_col", "period", "clearing_price"],
            COLUMN_MAPPING,
            {"trading_date", "period", "clearing_price"},
        )
        assert result is not None
        assert 0 in result
        assert 2 in result
        assert 3 in result
        assert 1 not in result


class TestDetectCsvEncoding:
    """CSV 编码检测测试。"""

    def test_utf8_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("交易日期,时段,出清价格\n")
            f.write("2025-01-01,1,100.00\n")
            path = Path(f.name)

        encoding = _detect_csv_encoding(path)
        assert encoding in ("utf-8-sig", "utf-8")
        path.unlink()


class TestConstants:
    """常量配置测试。"""

    def test_batch_size_is_1000(self):
        assert BATCH_SIZE == 1000

    def test_periods_per_day_is_96(self):
        assert PERIODS_PER_DAY == 96


# --- ImportContext 测试 ---


class TestImportContext:
    """ImportContext 状态跟踪测试。"""

    def test_add_anomaly_increments_counters(self):
        session = MagicMock()
        job = MagicMock()
        job.id = uuid.uuid4()
        job.success_records = 0
        job.failed_records = 0
        job.processed_records = 0

        ctx = ImportContext(session, job, 0)
        ctx.row_number = 5
        ctx.add_anomaly("format_error", "price", "abc", "格式错误")

        assert ctx.failed_records == 1
        assert ctx.processed_records == 1
        assert len(ctx.batch_anomalies) == 1
        assert ctx.batch_anomalies[0]["anomaly_type"] == "format_error"
        assert ctx.batch_anomalies[0]["row_number"] == 5

    def test_should_flush_on_batch_size(self):
        session = MagicMock()
        job = MagicMock()
        job.id = uuid.uuid4()
        job.success_records = 0
        job.failed_records = 0
        job.processed_records = 0

        ctx = ImportContext(session, job, 0)
        assert not ctx.should_flush()

        ctx.batch_records = [{}] * BATCH_SIZE
        assert ctx.should_flush()

    def test_should_flush_on_anomaly_size(self):
        session = MagicMock()
        job = MagicMock()
        job.id = uuid.uuid4()
        job.success_records = 0
        job.failed_records = 0
        job.processed_records = 0

        ctx = ImportContext(session, job, 0)
        ctx.batch_anomalies = [{}] * BATCH_SIZE
        assert ctx.should_flush()

    def test_flush_batch_calls_insert_and_commits(self):
        session = MagicMock()
        job = MagicMock()
        job.id = uuid.uuid4()
        job.success_records = 0
        job.failed_records = 0
        job.processed_records = 0

        ctx = ImportContext(session, job, 0)
        ctx.batch_records = [{"id": uuid.uuid4()}]
        ctx.row_number = 10
        ctx.processed_records = 10

        insert_fn = MagicMock(return_value=(1, 0))
        ctx.flush_batch(insert_fn)

        insert_fn.assert_called_once()
        session.commit.assert_called_once()
        assert ctx.success_records == 1
        assert not ctx.batch_records  # cleared
        assert not ctx.batch_anomalies  # cleared

    def test_flush_batch_handles_duplicates(self):
        session = MagicMock()
        job = MagicMock()
        job.id = uuid.uuid4()
        job.success_records = 0
        job.failed_records = 0
        job.processed_records = 0

        ctx = ImportContext(session, job, 0)
        ctx.batch_records = [{"id": uuid.uuid4()} for _ in range(3)]

        insert_fn = MagicMock(return_value=(2, 1))
        ctx.flush_batch(insert_fn)

        assert ctx.success_records == 2
        assert ctx.failed_records == 1


# --- Celery 任务核心逻辑测试 ---


def _create_csv_file(rows: list[list[str]], tmp_dir: Path) -> Path:
    """创建临时 CSV 文件。"""
    file_path = tmp_dir / "test.csv"
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    return file_path


def _make_mock_job(
    job_id: uuid.UUID,
    station_id: uuid.UUID,
    file_name: str,
    status: str = "pending",
):
    """创建模拟 DataImportJob 对象。"""
    job = MagicMock()
    job.id = job_id
    job.station_id = station_id
    job.file_name = file_name
    job.status = status
    job.total_records = 0
    job.processed_records = 0
    job.success_records = 0
    job.failed_records = 0
    job.data_completeness = Decimal("0")
    job.last_processed_row = 0
    job.celery_task_id = None
    job.started_at = None
    job.completed_at = None
    job.imported_by = uuid.uuid4()
    job.original_file_name = "test.csv"
    job.ems_format = None
    return job


def _make_mock_station(station_id: uuid.UUID, province: str = "广东"):
    station = MagicMock()
    station.id = station_id
    station.province = province
    return station


def _make_mock_market_rule(price_cap_lower: float = -100.0, price_cap_upper: float = 1500.0):
    rule = MagicMock()
    rule.price_cap_lower = price_cap_lower
    rule.price_cap_upper = price_cap_upper
    rule.is_active = True
    return rule


class TestExecuteImport:
    """_execute_import 核心导入逻辑测试。"""

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def setup_mocks(self, tmp_dir):
        """设置标准 mock 环境。"""
        job_id = uuid.uuid4()
        station_id = uuid.uuid4()

        session = MagicMock()
        task = MagicMock()
        task.request.id = "celery-task-123"

        station = _make_mock_station(station_id)
        market_rule = _make_mock_market_rule()

        # session.get 返回 job 或 station
        def session_get_side_effect(model, model_id):
            from app.models.data_import import DataImportJob
            from app.models.station import PowerStation
            if model == DataImportJob:
                return self._current_job
            if model == PowerStation:
                return station
            return None

        session.get.side_effect = session_get_side_effect

        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = market_rule
        mock_execute_result.rowcount = 3
        mock_execute_result.all.return_value = []
        session.execute.return_value = mock_execute_result

        return {
            "session": session,
            "task": task,
            "job_id": job_id,
            "station_id": station_id,
            "station": station,
            "market_rule": market_rule,
            "tmp_dir": tmp_dir,
            "mock_execute_result": mock_execute_result,
        }

    def _create_job_and_csv(self, setup_mocks, csv_rows):
        """创建 job 和 CSV 文件，返回 (job, job_id_str)。"""
        m = setup_mocks
        file_name = f"{m['job_id']}/test.csv"

        job = _make_mock_job(m["job_id"], m["station_id"], file_name)
        self._current_job = job

        return job, str(m["job_id"])

    @patch("app.tasks.import_tasks.settings")
    def test_csv_normal_import(self, mock_settings, setup_mocks):
        """正常 CSV 导入：3 行有效数据全部成功。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
            ["2025-01-01", "2", "200.00"],
            ["2025-01-01", "3", "300.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 3

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 3
        assert job.completed_at is not None

    @patch("app.tasks.import_tasks.settings")
    def test_csv_with_format_errors(self, mock_settings, setup_mocks):
        """格式错误：非数字价格标记为 format_error。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
            ["2025-01-01", "2", "abc"],
            ["invalid-date", "3", "300.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 1

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 3
        assert job.failed_records >= 2

    @patch("app.tasks.import_tasks.settings")
    def test_csv_with_out_of_range_price(self, mock_settings, setup_mocks):
        """超出省份限价的价格标记为 out_of_range。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])
        m["market_rule"].price_cap_lower = -100.0
        m["market_rule"].price_cap_upper = 1500.0

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
            ["2025-01-01", "2", "2000.00"],
            ["2025-01-01", "3", "-200.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 1

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 3
        assert job.failed_records >= 2

    @patch("app.tasks.import_tasks.settings")
    def test_resume_from_row(self, mock_settings, setup_mocks):
        """断点续传：跳过已处理行。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
            ["2025-01-01", "2", "200.00"],
            ["2025-01-01", "3", "300.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)
        job.processed_records = 2
        job.success_records = 2
        job.failed_records = 0

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 1

        _execute_import(m["session"], m["task"], job_id_str, resume_from_row=2)

        assert job.status == "completed"
        assert job.total_records == 3
        assert job.success_records >= 3

    @patch("app.tasks.import_tasks.settings")
    def test_chinese_column_headers(self, mock_settings, setup_mocks):
        """中文列头正确映射。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["交易日期", "时段", "出清价格"],
            ["2025-01-01", "1", "100.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 1

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 1

    @patch("app.tasks.import_tasks.settings")
    def test_job_not_found_raises(self, mock_settings, setup_mocks):
        """导入任务不存在时抛出 ValueError。"""
        m = setup_mocks
        self._current_job = None

        with pytest.raises(ValueError, match="not found"):
            _execute_import(m["session"], m["task"], str(uuid.uuid4()), 0)

    @patch("app.tasks.import_tasks.settings")
    def test_station_not_found_raises(self, mock_settings, setup_mocks):
        """电站不存在时抛出 ValueError。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        job = _make_mock_job(m["job_id"], m["station_id"], "test.csv")
        self._current_job = job

        from app.models.data_import import DataImportJob

        def get_side_effect(model, model_id):
            if model == DataImportJob:
                return job
            return None

        m["session"].get.side_effect = get_side_effect

        with pytest.raises(ValueError, match="Station"):
            _execute_import(m["session"], m["task"], str(m["job_id"]), 0)

    @patch("app.tasks.import_tasks.settings")
    def test_empty_file_raises(self, mock_settings, setup_mocks):
        """空文件抛出 ValueError。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows: list[list[str]] = []
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        with pytest.raises(ValueError, match="文件为空"):
            _execute_import(m["session"], m["task"], job_id_str, 0)

    @patch("app.tasks.import_tasks.settings")
    def test_invalid_columns_raises(self, mock_settings, setup_mocks):
        """列头不包含必要字段时抛出 ValueError。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["date", "price"],
            ["2025-01-01", "100.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        with pytest.raises(ValueError, match="列头映射失败"):
            _execute_import(m["session"], m["task"], job_id_str, 0)

    @patch("app.tasks.import_tasks.settings")
    def test_period_97_marked_as_format_error(self, mock_settings, setup_mocks):
        """时段编号 97 标记为 format_error。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "97", "100.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 0

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.failed_records >= 1

    @patch("app.tasks.import_tasks.settings")
    def test_data_completeness_calculated(self, mock_settings, setup_mocks):
        """数据完整性百分比正确计算。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
            ["2025-01-01", "2", "200.00"],
            ["2025-01-01", "3", "abc"],
            ["2025-01-01", "4", "400.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 3

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 4
        assert job.data_completeness > 0

    @patch("app.tasks.import_tasks.settings")
    def test_audit_log_written_on_completion(self, mock_settings, setup_mocks):
        """完成后写入审计日志。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        m["mock_execute_result"].rowcount = 1

        _execute_import(m["session"], m["task"], job_id_str, 0)

        m["session"].add.assert_called()
        audit_log = m["session"].add.call_args[0][0]
        assert audit_log.action == "complete_import_job"
        assert audit_log.resource_type == "data_import_job"


class TestProcessTradingDataImport:
    """process_trading_data_import Celery 任务测试。"""

    @patch("app.tasks.import_tasks.get_sync_session_factory")
    @patch("app.tasks.import_tasks._execute_import")
    def test_successful_import_closes_session(self, mock_execute, mock_factory):
        """成功导入后 session 正确关闭。"""
        from app.tasks.import_tasks import process_trading_data_import

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session

        job_id = str(uuid.uuid4())
        process_trading_data_import.run(job_id, 0)

        mock_session.close.assert_called_once()

    @patch("app.tasks.import_tasks.get_sync_session_factory")
    @patch("app.tasks.import_tasks._execute_import")
    def test_failed_import_marks_job_failed(self, mock_execute, mock_factory):
        """导入异常后 job 状态标记为 failed。"""
        from app.tasks.import_tasks import process_trading_data_import

        mock_session = MagicMock()
        mock_factory.return_value = lambda: mock_session
        mock_execute.side_effect = RuntimeError("Import exploded")

        mock_job = MagicMock()
        mock_session.get.return_value = mock_job

        job_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Import exploded"):
            process_trading_data_import.run(job_id, 0)

        mock_session.rollback.assert_called()
        assert mock_job.status == "failed"
        assert "Import exploded" in mock_job.error_message
        mock_session.close.assert_called_once()
