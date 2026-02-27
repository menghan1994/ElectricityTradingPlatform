import ipaddress
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import require_roles
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.repositories.user import UserRepository
from app.schemas.user import (
    AdminCreateUserResponse,
    AdminResetPasswordResponse,
    AdminUserCreate,
    RoleAssignRequest,
    StatusToggleRequest,
    UserListResponse,
    UserRead,
    UserUpdate,
)
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


def _validate_ip(value: str) -> str | None:
    """验证 IP 地址格式（IPv4/IPv6），非法值返回 None。"""
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        return None


def _get_client_ip(request: Request) -> str | None:
    """从请求中提取真实客户端 IP，支持反向代理（Nginx/Docker）环境。

    优先读取 X-Forwarded-For（取第一个 IP，即原始客户端），
    其次 X-Real-IP，最后回退到 request.client.host。
    所有来源均经过 ipaddress.ip_address() 格式验证，非法值回退到下一来源。
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        candidate = forwarded_for.split(",")[0].strip()
        validated = _validate_ip(candidate)
        if validated:
            return validated
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        validated = _validate_ip(real_ip.strip())
        if validated:
            return validated
    if request.client:
        return _validate_ip(request.client.host)
    return None


def _get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    user_repo = UserRepository(session)
    audit_repo = AuditLogRepository(session)
    audit_service = AuditService(audit_repo)
    return UserService(user_repo, audit_service)


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> UserListResponse:
    users, total = await user_service.list_users(page, page_size, search)
    return UserListResponse(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> UserRead:
    user = await user_service.get_user(user_id)
    return UserRead.model_validate(user)


@router.post("", response_model=AdminCreateUserResponse, status_code=201)
async def create_user(
    body: AdminUserCreate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> AdminCreateUserResponse:
    ip_address = _get_client_ip(request)
    user, temp_password = await user_service.create_user(current_user, body, ip_address)
    return AdminCreateUserResponse(
        user=UserRead.model_validate(user),
        temp_password=temp_password,
    )


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> UserRead:
    ip_address = _get_client_ip(request)
    user = await user_service.update_user(current_user, user_id, body, ip_address)
    return UserRead.model_validate(user)


@router.post("/{user_id}/reset_password", response_model=AdminResetPasswordResponse)
async def reset_password(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> AdminResetPasswordResponse:
    ip_address = _get_client_ip(request)
    temp_password = await user_service.reset_password(current_user, user_id, ip_address)
    return AdminResetPasswordResponse(temp_password=temp_password)


@router.put("/{user_id}/status", response_model=UserRead)
async def toggle_user_status(
    user_id: UUID,
    body: StatusToggleRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> UserRead:
    ip_address = _get_client_ip(request)
    user = await user_service.toggle_active(current_user, user_id, body.is_active, ip_address)
    return UserRead.model_validate(user)


@router.put("/{user_id}/role", response_model=UserRead)
async def assign_role(
    user_id: UUID,
    body: RoleAssignRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    user_service: UserService = Depends(_get_user_service),
) -> UserRead:
    ip_address = _get_client_ip(request)
    user = await user_service.assign_role(current_user, user_id, body.role, ip_address)
    return UserRead.model_validate(user)
