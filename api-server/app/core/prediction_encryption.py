"""功率预测模型 API Key 加解密工具。

M4 fix: 从 prediction_service.py 提取到独立模块，打破 schemas ↔ services 循环依赖。
"""

import base64
import hashlib

import structlog
from cryptography.fernet import Fernet

from app.core.config import settings

logger = structlog.get_logger()


def _get_fernet() -> Fernet:
    """获取 Fernet 加密实例（基于 ENCRYPTION_KEY 派生密钥）。"""
    prediction_key = getattr(settings, "PREDICTION_ENCRYPTION_KEY", None)
    if prediction_key:
        key = prediction_key
    else:
        key = settings.MARKET_DATA_ENCRYPTION_KEY
        logger.warning(
            "prediction_encryption_key_fallback",
            msg="PREDICTION_ENCRYPTION_KEY 未配置，回退使用 MARKET_DATA_ENCRYPTION_KEY",
        )
    key_bytes = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_api_key(api_key: str) -> bytes:
    """使用 Fernet (AES-128-CBC + HMAC-SHA256) 对称加密 API Key。"""
    f = _get_fernet()
    return f.encrypt(api_key.encode())


def decrypt_api_key(encrypted: bytes) -> str:
    """解密 API Key。"""
    f = _get_fernet()
    return f.decrypt(encrypted).decode()
