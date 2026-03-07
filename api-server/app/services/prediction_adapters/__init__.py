from app.models.prediction import PredictionModel
from app.services.prediction_adapters.base import BasePredictionAdapter, PredictionRecord
from app.services.prediction_adapters.generic import GenericPredictionAdapter


def get_adapter(model_config: PredictionModel, api_key: str | None = None) -> BasePredictionAdapter:
    """根据模型配置返回适配器实例。

    MVP 阶段仅支持通用 JSON API 适配器。
    后续可通过新增适配器类并在此工厂方法中路由来扩展。
    """
    return GenericPredictionAdapter(
        api_endpoint=model_config.api_endpoint,
        api_key=api_key,
        api_auth_type=model_config.api_auth_type,
        timeout_seconds=model_config.timeout_seconds,
    )
