from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.dependencies import get_current_active_user
from app.core.exceptions import BusinessError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshResponse,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter()

REFRESH_TOKEN_COOKIE_KEY = "refresh_token"
REFRESH_TOKEN_MAX_AGE = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400  # 7天秒数
REFRESH_TOKEN_PATH = "/api/v1/auth"


def _get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(UserRepository(session))


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    secure = settings.APP_ENV != "development"
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_TOKEN_PATH,
        max_age=REFRESH_TOKEN_MAX_AGE,
    )


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_KEY,
        path=REFRESH_TOKEN_PATH,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """用户登录：验证凭据，返回 Access Token + 设置 httpOnly Refresh Token Cookie。"""
    access_token, refresh_token = await auth_service.authenticate(
        body.username, body.password,
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    response: Response,
    auth_service: AuthService = Depends(_get_auth_service),
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_KEY),
) -> RefreshResponse:
    """从 Cookie 中的 Refresh Token 换取新的 Access Token。"""
    if not refresh_token:
        raise BusinessError(
            code="REFRESH_TOKEN_MISSING",
            message="未找到 Refresh Token",
            status_code=401,
        )
    new_access_token = await auth_service.refresh_access_token(refresh_token)
    return RefreshResponse(access_token=new_access_token)


@router.post("/logout")
async def logout(
    response: Response,
    _current_user: User = Depends(get_current_active_user),
) -> dict:
    """登出：清除 Refresh Token Cookie（需已认证）。"""
    _delete_refresh_cookie(response)
    return {"message": "登出成功"}


@router.post("/change_password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """修改密码（需已认证）。"""
    await auth_service.change_password(
        current_user.id, body.old_password, body.new_password,
    )
    return {"message": "密码修改成功"}


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    """返回当前登录用户信息。"""
    return UserRead.model_validate(current_user)
