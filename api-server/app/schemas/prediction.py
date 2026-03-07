import ipaddress
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.prediction_encryption import decrypt_api_key

ModelType = Literal["wind", "solar", "hybrid"]
ModelStatus = Literal["running", "error", "disabled"]
ApiAuthType = Literal["api_key", "bearer", "none"]
CheckStatus = Literal["success", "failed", "timeout"]

# 禁止访问的内部主机名
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}

# 禁止访问的私有/保留 IP 网段
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def _validate_endpoint_url(v: str) -> str:
    """验证 API 端点为合法的 HTTP(S) URL，防止 SSRF。"""
    stripped = v.strip()
    if not stripped:
        raise ValueError("API端点不能为空")
    parsed = urlparse(stripped)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("API端点必须以 http:// 或 https:// 开头")
    if not parsed.hostname:
        raise ValueError("API端点必须包含有效的主机名")
    hostname = parsed.hostname.lower()
    if hostname in _BLOCKED_HOSTS:
        raise ValueError("API端点不允许指向本地地址")
    # 检查 IP 地址是否属于私有/保留网段
    try:
        addr = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if addr in net:
                raise ValueError("API端点不允许指向内部网络地址")
    except ValueError as e:
        if "内部网络" in str(e) or "本地" in str(e):
            raise
        # hostname 不是 IP 地址（是域名），跳过网段检查
    return stripped


# --- 预测模型配置 schemas ---


class PredictionModelCreate(BaseModel):
    model_name: str
    model_type: ModelType = "wind"
    api_endpoint: str
    api_key: str | None = None
    api_auth_type: ApiAuthType = "api_key"
    call_frequency_cron: str = "0 6,12 * * *"
    timeout_seconds: int = 30
    station_id: UUID

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()

    @field_validator("api_endpoint")
    @classmethod
    def validate_api_endpoint(cls, v: str) -> str:
        return _validate_endpoint_url(v)

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0 or v > 300:
            raise ValueError("超时时间必须在1-300秒之间")
        return v


class PredictionModelUpdate(BaseModel):
    model_name: str | None = None
    model_type: ModelType | None = None
    api_endpoint: str | None = None
    api_key: str | None = None
    api_auth_type: ApiAuthType | None = None
    call_frequency_cron: str | None = None
    timeout_seconds: int | None = None
    is_active: bool | None = None

    @field_validator("api_endpoint")
    @classmethod
    def validate_api_endpoint(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_endpoint_url(v)
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int | None) -> int | None:
        if v is not None and (v <= 0 or v > 300):
            raise ValueError("超时时间必须在1-300秒之间")
        return v


class PredictionModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    station_id: UUID
    model_name: str
    model_type: ModelType
    api_endpoint: str
    api_key_display: str | None = None
    api_auth_type: ApiAuthType
    call_frequency_cron: str
    timeout_seconds: int
    is_active: bool
    status: ModelStatus
    last_check_at: datetime | None
    last_check_status: str | None
    last_check_error: str | None
    last_fetch_at: datetime | None = None
    last_fetch_status: str | None = None
    last_fetch_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: object) -> "PredictionModelRead":
        """从 ORM 模型创建，api_key 脱敏显示。"""
        data = {
            "id": model.id,  # type: ignore[attr-defined]
            "station_id": model.station_id,  # type: ignore[attr-defined]
            "model_name": model.model_name,  # type: ignore[attr-defined]
            "model_type": model.model_type,  # type: ignore[attr-defined]
            "api_endpoint": model.api_endpoint,  # type: ignore[attr-defined]
            "api_auth_type": model.api_auth_type,  # type: ignore[attr-defined]
            "call_frequency_cron": model.call_frequency_cron,  # type: ignore[attr-defined]
            "timeout_seconds": model.timeout_seconds,  # type: ignore[attr-defined]
            "is_active": model.is_active,  # type: ignore[attr-defined]
            "status": model.status,  # type: ignore[attr-defined]
            "last_check_at": model.last_check_at,  # type: ignore[attr-defined]
            "last_check_status": model.last_check_status,  # type: ignore[attr-defined]
            "last_check_error": model.last_check_error,  # type: ignore[attr-defined]
            "last_fetch_at": model.last_fetch_at,  # type: ignore[attr-defined]
            "last_fetch_status": model.last_fetch_status,  # type: ignore[attr-defined]
            "last_fetch_error": model.last_fetch_error,  # type: ignore[attr-defined]
            "created_at": model.created_at,  # type: ignore[attr-defined]
            "updated_at": model.updated_at,  # type: ignore[attr-defined]
        }
        # api_key 脱敏：仅显示后4位（M4 fix: 使用顶层 import 替代内联 import）
        if model.api_key_encrypted:  # type: ignore[attr-defined]
            try:
                decrypted = decrypt_api_key(model.api_key_encrypted)  # type: ignore[attr-defined]
                if len(decrypted) >= 4:
                    data["api_key_display"] = "****" + decrypted[-4:]
                else:
                    data["api_key_display"] = "****"
            except Exception:
                data["api_key_display"] = "****"
        else:
            data["api_key_display"] = None
        return cls(**data)


class PredictionModelListResponse(BaseModel):
    items: list[PredictionModelRead]
    total: int
    page: int
    page_size: int


# --- 模型运行状态 schemas ---


class PredictionModelStatus(BaseModel):
    model_id: UUID
    model_name: str
    station_name: str | None = None
    status: ModelStatus
    last_check_at: datetime | None
    last_check_error: str | None
    last_fetch_at: datetime | None = None
    last_fetch_status: str | None = None
    last_fetch_error: str | None = None


class PredictionModelStatusListResponse(BaseModel):
    items: list[PredictionModelStatus]


# --- 连接测试 schemas ---


class ConnectionTestResult(BaseModel):
    success: bool
    latency_ms: float | None = None
    error_message: str | None = None
    tested_at: datetime


# --- 功率预测数据 schemas ---


class PowerPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prediction_date: date
    period: int
    predicted_power_kw: Decimal
    confidence_upper_kw: Decimal
    confidence_lower_kw: Decimal
    source: str
    fetched_at: datetime

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: int) -> int:
        if v < 1 or v > 96:
            raise ValueError("时段编号必须在1-96之间")
        return v

    @field_validator("predicted_power_kw")
    @classmethod
    def validate_power(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("预测功率不能为负")
        return v

    @field_validator("confidence_upper_kw")
    @classmethod
    def validate_confidence_upper(cls, v: Decimal, info) -> Decimal:
        predicted = info.data.get("predicted_power_kw")
        if predicted is not None and v < predicted:
            raise ValueError("置信区间上限不能小于预测值")
        return v

    @field_validator("confidence_lower_kw")
    @classmethod
    def validate_confidence_lower(cls, v: Decimal, info) -> Decimal:
        predicted = info.data.get("predicted_power_kw")
        if predicted is not None and v > predicted:
            raise ValueError("置信区间下限不能大于预测值")
        return v


class PowerPredictionListResponse(BaseModel):
    items: list[PowerPredictionRead]
    total: int


class FetchResult(BaseModel):
    model_id: UUID
    model_name: str
    station_name: str | None = None
    success: bool
    records_count: int = 0
    error_message: str | None = None
    fetched_at: datetime
