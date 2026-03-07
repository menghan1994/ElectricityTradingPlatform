import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.services.prediction_adapters.base import PredictionRecord
from app.tasks.prediction_tasks import check_prediction_models_health, fetch_prediction_data_for_all_models


class TestCheckPredictionModelsHealth:
    """check_prediction_models_health Celery 任务测试。"""

    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_no_active_models(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = check_prediction_models_health()
        assert result == {"status": "no_active_models"}

    @patch("app.tasks.prediction_tasks.asyncio.run")
    @patch("app.tasks.prediction_tasks.get_adapter")
    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_healthy_model(self, mock_session_factory, mock_get_adapter, mock_asyncio_run):
        model = MagicMock()
        model.id = uuid.uuid4()
        model.model_name = "风电预测模型"
        model.api_key_encrypted = None
        model.status = "running"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        # batch health check returns [True]
        mock_asyncio_run.return_value = [True]

        result = check_prediction_models_health()
        assert str(model.id) in result
        assert result[str(model.id)] == "running"

    @patch("app.tasks.prediction_tasks.asyncio.run")
    @patch("app.tasks.prediction_tasks.get_adapter")
    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_unhealthy_model_triggers_warning(
        self, mock_session_factory, mock_get_adapter, mock_asyncio_run,
    ):
        model = MagicMock()
        model.id = uuid.uuid4()
        model.model_name = "异常模型"
        model.api_key_encrypted = None
        model.status = "running"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        # batch health check returns [False]
        mock_asyncio_run.return_value = [False]

        result = check_prediction_models_health()
        assert result[str(model.id)] == "error"
        update_calls = [
            c for c in mock_session.execute.call_args_list
            if "update" in str(c).lower() or "UPDATE" in str(c)
        ]
        assert len(update_calls) > 0, "Expected SQL UPDATE to be executed for status change"

    @patch("app.tasks.prediction_tasks.asyncio.run")
    @patch("app.tasks.prediction_tasks.get_adapter")
    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_health_check_exception(
        self, mock_session_factory, mock_get_adapter, mock_asyncio_run,
    ):
        model = MagicMock()
        model.id = uuid.uuid4()
        model.model_name = "异常模型"
        model.api_key_encrypted = None
        model.status = "running"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        # batch health check returns [Exception]
        mock_asyncio_run.return_value = [RuntimeError("连接超时")]

        result = check_prediction_models_health()
        model_key = str(model.id)
        assert model_key in result
        assert "error" in result[model_key]


class TestFetchPredictionDataForAllModels:
    """fetch_prediction_data_for_all_models Celery 任务测试。"""

    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_no_running_models(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        result = fetch_prediction_data_for_all_models()
        assert result == {"status": "no_running_models"}

    @patch("app.tasks.prediction_tasks.validate_prediction_records")
    @patch("app.tasks.prediction_tasks.asyncio.run")
    @patch("app.tasks.prediction_tasks.get_adapter")
    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_successful_fetch(
        self, mock_session_factory, mock_get_adapter, mock_asyncio_run, mock_validate,
    ):
        model = MagicMock()
        model.id = uuid.uuid4()
        model.model_name = "风电预测模型"
        model.station_id = uuid.uuid4()
        model.api_key_encrypted = None
        model.status = "running"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        records = [
            PredictionRecord(
                period=i,
                predicted_power_kw=Decimal("1500"),
                confidence_upper_kw=Decimal("1650"),
                confidence_lower_kw=Decimal("1350"),
            )
            for i in range(1, 97)
        ]
        mock_asyncio_run.return_value = [records]
        mock_validate.return_value = (records, [])

        result = fetch_prediction_data_for_all_models()
        assert str(model.id) in result
        assert result[str(model.id)] == "success"

    @patch("app.tasks.prediction_tasks.asyncio.run")
    @patch("app.tasks.prediction_tasks.get_adapter")
    @patch("app.tasks.prediction_tasks.get_sync_session_factory")
    def test_fetch_exception_isolated(
        self, mock_session_factory, mock_get_adapter, mock_asyncio_run,
    ):
        model = MagicMock()
        model.id = uuid.uuid4()
        model.model_name = "失败模型"
        model.station_id = uuid.uuid4()
        model.api_key_encrypted = None
        model.status = "running"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value = MagicMock(return_value=mock_session)

        mock_asyncio_run.return_value = [RuntimeError("API调用失败")]

        result = fetch_prediction_data_for_all_models()
        assert str(model.id) in result
        assert result[str(model.id)] == "failed"
