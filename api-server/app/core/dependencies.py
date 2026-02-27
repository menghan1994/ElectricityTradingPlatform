from uuid import UUID

import jwt
import structlog
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.exceptions import BusinessError
from app.core.security import JWT_ALGORITHM

logger = structlog.get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
):
    """从 Bearer Token 解析当前用户。"""
    from app.models.user import User

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise BusinessError(
            code="TOKEN_EXPIRED",
            message="Token 已过期",
            status_code=401,
        )
    except jwt.InvalidTokenError:
        raise BusinessError(
            code="TOKEN_INVALID",
            message="Token 格式错误或签名无效",
            status_code=401,
        )

    if payload.get("type") != "access":
        raise BusinessError(
            code="TOKEN_INVALID",
            message="Token 类型错误",
            status_code=401,
        )

    user_id = payload.get("sub")
    if not user_id:
        raise BusinessError(
            code="TOKEN_INVALID",
            message="Token 缺少用户标识",
            status_code=401,
        )

    user = await session.get(User, UUID(user_id))
    if not user:
        raise BusinessError(
            code="TOKEN_INVALID",
            message="用户不存在",
            status_code=401,
        )

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """校验当前用户未停用且未锁定。"""
    from datetime import UTC, datetime

    if not current_user.is_active:
        raise BusinessError(
            code="ACCOUNT_DISABLED",
            message="账户已停用",
            status_code=403,
        )

    if current_user.is_locked and current_user.locked_until:
        if current_user.locked_until > datetime.now(UTC):
            remaining = (current_user.locked_until - datetime.now(UTC)).seconds // 60
            raise BusinessError(
                code="ACCOUNT_LOCKED",
                message="账户已锁定",
                detail={"remaining_minutes": remaining + 1},
                status_code=403,
            )

    return current_user
