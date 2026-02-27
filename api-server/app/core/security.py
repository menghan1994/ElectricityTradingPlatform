import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"

# 密码强度规则
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72  # bcrypt 5.0.0 限制
PASSWORD_RULES_ZH = [
    "密码长度至少8个字符",
    "必须包含至少1个大写字母",
    "必须包含至少1个小写字母",
    "必须包含至少1个数字",
    "必须包含至少1个特殊字符（如 !@#$%^&*）",
]


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希。rounds=14 约1秒哈希时间。"""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > PASSWORD_MAX_BYTES:
        raise ValueError(f"密码超过 {PASSWORD_MAX_BYTES} 字节限制")
    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(rounds=14),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与 bcrypt 哈希是否匹配。超长密码直接返回 False。"""
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > PASSWORD_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> list[str]:
    """校验密码强度，返回不满足规则的列表。空列表表示通过。"""
    violations: list[str] = []

    if len(password) < PASSWORD_MIN_LENGTH:
        violations.append(PASSWORD_RULES_ZH[0])
    if not re.search(r"[A-Z]", password):
        violations.append(PASSWORD_RULES_ZH[1])
    if not re.search(r"[a-z]", password):
        violations.append(PASSWORD_RULES_ZH[2])
    if not re.search(r"[0-9]", password):
        violations.append(PASSWORD_RULES_ZH[3])
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:'\",.<>?/`~]", password):
        violations.append(PASSWORD_RULES_ZH[4])
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        violations.append(f"密码不能超过{PASSWORD_MAX_BYTES}字节")

    return violations


def create_access_token(user_id: UUID, username: str, role: str = "trader") -> str:
    """生成 Access Token（30分钟有效期）。"""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """生成 Refresh Token（7天有效期）。"""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT Token。失败时抛出 jwt.InvalidTokenError 或其子类。"""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
