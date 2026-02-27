from datetime import UTC, datetime
from uuid import UUID

import jwt
import structlog

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.security import (
    JWT_ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.repositories.user import UserRepository

logger = structlog.get_logger()

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate(self, username: str, password: str) -> tuple[str, str]:
        """认证用户，返回 (access_token, refresh_token)。"""
        user = await self.user_repo.get_by_username(username)

        # 不泄露用户是否存在
        if not user:
            logger.warning("login_failed", reason="user_not_found", username=username)
            raise BusinessError(
                code="INVALID_CREDENTIALS",
                message="用户名或密码错误",
                status_code=401,
            )

        # 检查账户是否停用
        if not user.is_active:
            logger.warning("login_failed", reason="account_disabled", username=username)
            raise BusinessError(
                code="ACCOUNT_DISABLED",
                message="账户已停用",
                status_code=403,
            )

        # 检查账户锁定
        if user.is_locked and user.locked_until:
            if user.locked_until > datetime.now(UTC):
                remaining = int((user.locked_until - datetime.now(UTC)).total_seconds() / 60) + 1
                logger.warning("login_failed", reason="account_locked", username=username, remaining_minutes=remaining)
                raise BusinessError(
                    code="ACCOUNT_LOCKED",
                    message="账户已锁定",
                    detail={"remaining_minutes": remaining},
                    status_code=403,
                )
            else:
                # 锁定已过期，自动解锁
                await self.user_repo.reset_failed_attempts(user)

        # 验证密码
        if not verify_password(password, user.hashed_password):
            await self.user_repo.increment_failed_attempts(user)
            logger.warning(
                "login_failed",
                reason="invalid_password",
                username=username,
                failed_attempts=user.failed_login_attempts,
            )

            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                await self.user_repo.lock_account(user, LOCK_MINUTES)
                logger.warning("account_locked", username=username, lock_minutes=LOCK_MINUTES)

            raise BusinessError(
                code="INVALID_CREDENTIALS",
                message="用户名或密码错误",
                status_code=401,
            )

        # 登录成功
        await self.user_repo.reset_failed_attempts(user)
        await self.user_repo.update_last_login(user)

        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id)

        logger.info("login_success", username=username, user_id=str(user.id))
        return access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> str:
        """从 Refresh Token 换取新的 Access Token。"""
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise BusinessError(
                code="TOKEN_EXPIRED",
                message="Refresh Token 已过期",
                status_code=401,
            )
        except jwt.InvalidTokenError:
            raise BusinessError(
                code="TOKEN_INVALID",
                message="Refresh Token 无效",
                status_code=401,
            )

        if payload.get("type") != "refresh":
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

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise BusinessError(
                code="TOKEN_INVALID",
                message="用户不存在或已停用",
                status_code=401,
            )

        return create_access_token(user.id, user.username)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """修改密码：验证旧密码 + 校验新密码强度 + 更新哈希。"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(
                code="TOKEN_INVALID",
                message="用户不存在",
                status_code=401,
            )

        if not verify_password(old_password, user.hashed_password):
            raise BusinessError(
                code="PASSWORD_MISMATCH",
                message="旧密码不正确",
                status_code=400,
            )

        violations = validate_password_strength(new_password)
        if violations:
            raise BusinessError(
                code="PASSWORD_TOO_WEAK",
                message="密码不满足强度要求",
                detail={"violations": violations},
                status_code=422,
            )

        hashed = hash_password(new_password)
        await self.user_repo.update_password(user, hashed)
        logger.info("password_changed", user_id=str(user_id))
