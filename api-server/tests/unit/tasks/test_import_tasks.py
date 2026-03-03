import csv
import tempfile
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from app.tasks.import_tasks import (
    BATCH_SIZE,
    SyncBatchWriter,
    _check_period_completeness,
    _detect_csv_encoding,
    _execute_import,
    _map_columns,
    _parse_date,
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


class TestMapColumns:
    """列头映射测试。"""

    def test_english_columns(self):
        result = _map_columns(["trading_date", "period", "clearing_price"])
        assert result is not None
        assert result[0] == "trading_date"
        assert result[1] == "period"
        assert result[2] == "clearing_price"

    def test_chinese_columns(self):
        result = _map_columns(["交易日期", "时段", "出清价格"])
        assert result is not None
        assert result[0] == "trading_date"
        assert result[1] == "period"
        assert result[2] == "clearing_price"

    def test_mixed_case(self):
        result = _map_columns(["Trading_Date", "Period", "Clearing_Price"])
        assert result is not None

    def test_missing_column(self):
        result = _map_columns(["trading_date", "period"])
        assert result is None

    def test_extra_columns_ignored(self):
        result = _map_columns(["trading_date", "extra_col", "period", "clearing_price"])
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


class TestBatchSize:
    """批量大小配置测试。"""

    def test_batch_size_is_1000(self):
        assert BATCH_SIZE == 1000


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


class TestSyncBatchWriter:
    """SyncBatchWriter 批量写入器测试。"""

    def test_insert_trading_records_empty(self):
        session = MagicMock()
        writer = SyncBatchWriter(session)
        inserted, dup_count, anomalies = writer.insert_trading_records([], uuid.uuid4())
        assert inserted == 0
        assert dup_count == 0
        assert anomalies == []
        session.execute.assert_not_called()

    def test_insert_trading_records_all_inserted(self):
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        session.execute.return_value = mock_result

        writer = SyncBatchWriter(session)
        records = [
            {"id": uuid.uuid4(), "trading_date": date(2025, 1, 1), "period": i,
             "station_id": uuid.uuid4(), "clearing_price": Decimal("100"),
             "import_job_id": uuid.uuid4()}
            for i in range(1, 4)
        ]
        inserted, dup_count, anomalies = writer.insert_trading_records(records, uuid.uuid4())
        assert inserted == 3
        assert dup_count == 0
        assert anomalies == []

    def test_insert_trading_records_with_duplicates(self):
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 2  # 3 records, 1 duplicate
        session.execute.return_value = mock_result

        writer = SyncBatchWriter(session)
        job_uuid = uuid.uuid4()
        records = [
            {"id": uuid.uuid4(), "trading_date": date(2025, 1, 1), "period": i,
             "station_id": uuid.uuid4(), "clearing_price": Decimal("100"),
             "import_job_id": job_uuid}
            for i in range(1, 4)
        ]
        inserted, dup_count, anomalies = writer.insert_trading_records(records, job_uuid)
        assert inserted == 2
        assert dup_count == 1
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_type"] == "duplicate"
        assert "1 条重复记录" in anomalies[0]["description"]

    def test_insert_anomalies_empty(self):
        session = MagicMock()
        writer = SyncBatchWriter(session)
        writer.insert_anomalies([])
        session.execute.assert_not_called()

    def test_insert_anomalies_non_empty(self):
        session = MagicMock()
        writer = SyncBatchWriter(session)
        anomalies = [{"id": uuid.uuid4(), "anomaly_type": "format_error"}]
        writer.insert_anomalies(anomalies)
        session.execute.assert_called_once()

    def test_flush_batch_commits_and_returns_counts(self):
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        session.execute.return_value = mock_result

        writer = SyncBatchWriter(session)
        job = MagicMock()
        job_uuid = uuid.uuid4()
        records = [{"id": uuid.uuid4()} for _ in range(5)]

        inserted, dup_count = writer.flush_batch(
            job, records, [], job_uuid, 10, 5, 0, 10,
        )
        assert inserted == 5
        assert dup_count == 0
        session.commit.assert_called_once()
        assert job.processed_records == 10
        assert job.success_records == 10  # 5 + inserted(5)
        assert job.last_processed_row == 10


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

        # session.query(...).filter(...).first() 返回 market_rule
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = market_rule
        mock_query.filter.return_value = mock_filter
        session.query.return_value = mock_query

        return {
            "session": session,
            "task": task,
            "job_id": job_id,
            "station_id": station_id,
            "station": station,
            "market_rule": market_rule,
            "tmp_dir": tmp_dir,
        }

    def _create_job_and_csv(self, setup_mocks, csv_rows):
        """创建 job 和 CSV 文件，返回 (job, job_id_str)。"""
        m = setup_mocks
        file_path = _create_csv_file(csv_rows, m["tmp_dir"])
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

        # 创建文件到正确路径
        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)
        job.file_name = f"{m['job_id']}/test.csv"

        # Mock SyncBatchWriter 的 insert 方法
        mock_result = MagicMock()
        mock_result.rowcount = 3
        m["session"].execute.return_value = mock_result

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
            ["2025-01-01", "1", "100.00"],  # 正常
            ["2025-01-01", "2", "abc"],      # 价格格式错误
            ["invalid-date", "3", "300.00"],  # 日期格式错误
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 3
        # 2 行校验失败（价格格式 + 日期格式）
        assert job.failed_records >= 2

    @patch("app.tasks.import_tasks.settings")
    def test_csv_with_out_of_range_price(self, mock_settings, setup_mocks):
        """超出省份限价的价格标记为 out_of_range。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])
        # 设置限价范围 -100 ~ 1500
        m["market_rule"].price_cap_lower = -100.0
        m["market_rule"].price_cap_upper = 1500.0

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],    # 正常
            ["2025-01-01", "2", "2000.00"],   # 超出上限
            ["2025-01-01", "3", "-200.00"],   # 超出下限
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 3
        # 2 行超出限价范围
        assert job.failed_records >= 2

    @patch("app.tasks.import_tasks.settings")
    def test_resume_from_row(self, mock_settings, setup_mocks):
        """断点续传：跳过已处理行。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        csv_rows = [
            ["trading_date", "period", "clearing_price"],
            ["2025-01-01", "1", "100.00"],  # row 1 — 应跳过
            ["2025-01-01", "2", "200.00"],  # row 2 — 应跳过
            ["2025-01-01", "3", "300.00"],  # row 3 — 应处理
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)
        # 模拟已处理了前 2 行
        job.processed_records = 2
        job.success_records = 2
        job.failed_records = 0

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, resume_from_row=2)

        assert job.status == "completed"
        assert job.total_records == 3
        # success_records 应包含之前的 2 + 新处理的 1
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

        mock_result = MagicMock()
        mock_result.rowcount = 1
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 1

    @patch("app.tasks.import_tasks.settings")
    def test_job_not_found_raises(self, mock_settings, setup_mocks):
        """导入任务不存在时抛出 ValueError。"""
        m = setup_mocks
        self._current_job = None  # session.get 返回 None

        with pytest.raises(ValueError, match="not found"):
            _execute_import(m["session"], m["task"], str(uuid.uuid4()), 0)

    @patch("app.tasks.import_tasks.settings")
    def test_station_not_found_raises(self, mock_settings, setup_mocks):
        """电站不存在时抛出 ValueError。"""
        m = setup_mocks
        mock_settings.DATA_IMPORT_DIR = str(m["tmp_dir"])

        job = _make_mock_job(m["job_id"], m["station_id"], "test.csv")
        self._current_job = job

        # 覆盖 session.get 使 station 返回 None
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

        csv_rows: list[list[str]] = []  # 空文件
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
            ["date", "price"],  # 缺少 period 列
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

        mock_result = MagicMock()
        mock_result.rowcount = 0
        m["session"].execute.return_value = mock_result

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
            ["2025-01-01", "3", "abc"],  # format error
            ["2025-01-01", "4", "400.00"],
        ]
        job, job_id_str = self._create_job_and_csv(m, csv_rows)

        job_dir = m["tmp_dir"] / str(m["job_id"])
        job_dir.mkdir(exist_ok=True)
        _create_csv_file(csv_rows, job_dir)

        mock_result = MagicMock()
        mock_result.rowcount = 3  # 3 inserted successfully
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, 0)

        assert job.status == "completed"
        assert job.total_records == 4
        # data_completeness should be > 0
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

        mock_result = MagicMock()
        mock_result.rowcount = 1
        m["session"].execute.return_value = mock_result

        _execute_import(m["session"], m["task"], job_id_str, 0)

        # 验证 session.add 被调用（审计日志）
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
        # bind=True: .run() 自动注入 task self，只传 job_id 和 resume_from_row
        process_trading_data_import.run(job_id, 0)

        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0]
        assert call_args[0] is mock_session
        assert call_args[2] == job_id
        assert call_args[3] == 0
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

        # 验证 rollback 被调用
        mock_session.rollback.assert_called()
        # 验证 job 状态被更新为 failed
        assert mock_job.status == "failed"
        assert "Import exploded" in mock_job.error_message
        mock_session.close.assert_called_once()
