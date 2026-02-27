import asyncio
import secrets
import string
from typing import get_args
from uuid import UUID

import structlog

from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.user import AdminUserCreate, RoleType, UserUpdate
from app.services.audit_service import AuditService

# 从 RoleType Literal 派生的合法角色集合，用于运行时防御（非 HTTP 调用方绕过 Schema 校验）
_VALID_ROLES: frozenset[str] = frozenset(get_args(RoleType))

logger = structlog.get_logger()


def generate_temp_password(length: int = 12) -> str:
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    remaining = length - len(password)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password.extend(secrets.choice(alphabet) for _ in range(remaining))
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


SAFE_UPDATE_FIELDS = frozenset({"display_name", "phone", "email"})


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        audit_service: AuditService,
    ):
        self.user_repo = user_repo
        self.audit_service = audit_service

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    async def create_user(
        self, admin_user: User, data: AdminUserCreate, ip_address: str | None = None,
    ) -> tuple[User, str]:
        self._warn_if_no_ip("create_user", ip_address)
        if data.role not in _VALID_ROLES:
            raise BusinessError(code="INVALID_ROLE", message="角色值无效", status_code=422)

        existing = await self.user_repo.get_by_username(data.username)
        if existing:
            raise BusinessError(code="USERNAME_EXISTS", message="用户名已被注册", status_code=409)

        if data.email is not None:
            existing_email = await self.user_repo.get_by_email(data.email)
            if existing_email:
                raise BusinessError(code="EMAIL_EXISTS", message="邮箱已被使用", status_code=409)

        temp_password = generate_temp_password()
        hashed = await asyncio.to_thread(hash_password, temp_password)

        user = User(
            username=data.username,
            hashed_password=hashed,
            display_name=data.display_name,
            phone=data.phone,
            email=data.email,
            role=data.role,
        )
        created_user = await self.user_repo.create(user)

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="create_user",
            resource_type="user",
            resource_id=created_user.id,
            changes_after={
                "username": created_user.username,
                "display_name": created_user.display_name,
                "role": created_user.role,
            },
            ip_address=ip_address,
        )

        logger.info("user_created", username=data.username, role=data.role, admin=admin_user.username)
        return created_user, temp_password

    async def update_user(
        self, admin_user: User, user_id: UUID, data: UserUpdate, ip_address: str | None = None,
    ) -> User:
        self._warn_if_no_ip("update_user", ip_address)
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

        changes_before: dict = {}
        changes_after: dict = {}

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] is not None and update_data["email"] != user.email:
            existing_email = await self.user_repo.get_by_email(update_data["email"])
            if existing_email and existing_email.id != user.id:
                raise BusinessError(code="EMAIL_EXISTS", message="邮箱已被使用", status_code=409)

        for field, value in update_data.items():
            if field not in SAFE_UPDATE_FIELDS:
                continue
            old_value = getattr(user, field)
            if old_value != value:
                changes_before[field] = old_value
                changes_after[field] = value
                setattr(user, field, value)

        if changes_after:
            await self.user_repo.session.flush()
            await self.user_repo.session.refresh(user)
            await self.audit_service.log_action(
                user_id=admin_user.id,
                action="update_user",
                resource_type="user",
                resource_id=user_id,
                changes_before=changes_before,
                changes_after=changes_after,
                ip_address=ip_address,
            )
            logger.info("user_updated", target_user=user.username, changes=list(changes_after.keys()), admin=admin_user.username)

        return user

    async def reset_password(
        self, admin_user: User, user_id: UUID, ip_address: str | None = None,
    ) -> str:
        self._warn_if_no_ip("reset_password", ip_address)
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

        temp_password = generate_temp_password()
        hashed = await asyncio.to_thread(hash_password, temp_password)
        await self.user_repo.update_password(user, hashed)

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="reset_password",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip_address,
        )

        logger.info("password_reset", target_user=user.username, admin=admin_user.username)
        return temp_password

    async def toggle_active(
        self, admin_user: User, user_id: UUID, is_active: bool, ip_address: str | None = None,
    ) -> User:
        self._warn_if_no_ip("toggle_active", ip_address)
        if user_id == admin_user.id:
            raise BusinessError(code="CANNOT_MODIFY_SELF", message="管理员不能停用自己的账户", status_code=403)

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

        old_active = user.is_active
        if old_active == is_active:
            return user

        user.is_active = is_active
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user)

        action = "enable_user" if is_active else "disable_user"
        await self.audit_service.log_action(
            user_id=admin_user.id,
            action=action,
            resource_type="user",
            resource_id=user_id,
            changes_before={"is_active": old_active},
            changes_after={"is_active": is_active},
            ip_address=ip_address,
        )

        logger.info("user_status_changed", target_user=user.username, is_active=is_active, admin=admin_user.username)
        return user

    async def assign_role(
        self, admin_user: User, user_id: UUID, role: RoleType, ip_address: str | None = None,
    ) -> User:
        self._warn_if_no_ip("assign_role", ip_address)
        if role not in _VALID_ROLES:
            raise BusinessError(code="INVALID_ROLE", message="角色值无效", status_code=422)

        if user_id == admin_user.id and role != UserRole.ADMIN:
            raise BusinessError(code="CANNOT_MODIFY_SELF", message="管理员不能降级自己的角色", status_code=403)

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)

        old_role = user.role
        if old_role == role:
            return user

        user.role = role
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user)

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="assign_role",
            resource_type="user",
            resource_id=user_id,
            changes_before={"role": old_role},
            changes_after={"role": role},
            ip_address=ip_address,
        )

        logger.info("role_assigned", target_user=user.username, old_role=old_role, new_role=role, admin=admin_user.username)
        return user

    async def list_users(
        self, page: int = 1, page_size: int = 20, search: str | None = None,
    ) -> tuple[list[User], int]:
        return await self.user_repo.get_all_paginated(page, page_size, search)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)
        return user
