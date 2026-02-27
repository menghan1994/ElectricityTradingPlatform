"""认证 API 路由层测试 — 使用 dependency_overrides Mock AuthService，
仅验证 API 层路由/参数解析/响应格式是否正确。
注意：业务逻辑（密码验证、锁定等）由 tests/unit/services/test_auth_service.py 覆盖。
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.main import app
from app.models.user import User


def _make_user_obj(
    username: str = "testuser",
    password: str = "Test@1234",
    is_active: bool = True,
    is_locked: bool = False,
    locked_until: datetime | None = None,
    failed_login_attempts: int = 0,
    role: str = "trader",
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = username
    user.hashed_password = hash_password(password)
    user.display_name = "测试用户"
    user.phone = None
    user.email = None
    user.role = role
    user.is_active = is_active
    user.is_locked = is_locked
    user.locked_until = locked_until
    user.failed_login_attempts = failed_login_attempts
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _create_mock_auth_service(user: MagicMock | None = None):
    """创建一个 mock 的 AuthService 工厂，通过 dependency_overrides 注入。"""
    from app.repositories.user import UserRepository
    from app.services.auth_service import AuthService

    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_username.return_value = user
    mock_repo.get_by_id.return_value = user
    mock_repo.reset_failed_attempts.return_value = None
    mock_repo.update_last_login.return_value = None
    mock_repo.increment_failed_attempts.return_value = None
    mock_repo.lock_account.return_value = None
    mock_repo.update_password.return_value = None

    service = AuthService(mock_repo)
    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # 清除所有 dependency overrides
    app.dependency_overrides.clear()


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_success(self, api_client):
        user = _make_user_obj()
        service = _create_mock_auth_service(user)

        from app.api.v1.auth import _get_auth_service
        app.dependency_overrides[_get_auth_service] = lambda: service

        response = await api_client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "Test@1234",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, api_client):
        service = _create_mock_auth_service(None)  # 用户不存在

        from app.api.v1.auth import _get_auth_service
        app.dependency_overrides[_get_auth_service] = lambda: service

        response = await api_client.post("/api/v1/auth/login", json={
            "username": "wrong",
            "password": "Wrong@1234",
        })

        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_account_locked(self, api_client):
        user = _make_user_obj(
            is_locked=True,
            locked_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        service = _create_mock_auth_service(user)

        from app.api.v1.auth import _get_auth_service
        app.dependency_overrides[_get_auth_service] = lambda: service

        response = await api_client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "Test@1234",
        })

        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "ACCOUNT_LOCKED"
        assert "remaining_minutes" in data["detail"]


class TestRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_refresh_missing_cookie(self, api_client):
        response = await api_client.post("/api/v1/auth/refresh")

        assert response.status_code == 401
        assert response.json()["code"] == "REFRESH_TOKEN_MISSING"

    @pytest.mark.asyncio
    async def test_refresh_success(self, api_client):
        user = _make_user_obj()
        refresh_token = create_refresh_token(user.id)
        service = _create_mock_auth_service(user)

        from app.api.v1.auth import _get_auth_service
        app.dependency_overrides[_get_auth_service] = lambda: service

        # 使用 Cookie header 直接传递 refresh_token
        response = await api_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": f"refresh_token={refresh_token}"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_logout(self, api_client):
        user = _make_user_obj()

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        access_token = create_access_token(user.id, user.username)
        response = await api_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "登出成功"

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, api_client):
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides.pop(get_current_active_user, None)

        response = await api_client.post("/api/v1/auth/logout")

        assert response.status_code in (401, 403)


class TestChangePasswordEndpoint:
    @pytest.mark.asyncio
    async def test_change_password_success(self, api_client):
        user = _make_user_obj(password="OldPass@123")
        access_token = create_access_token(user.id, user.username)
        service = _create_mock_auth_service(user)

        from app.api.v1.auth import _get_auth_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[_get_auth_service] = lambda: service
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.post(
            "/api/v1/auth/change_password",
            json={"old_password": "OldPass@123", "new_password": "NewPass@456"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_get_me_success(self, api_client):
        user = _make_user_obj()

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        access_token = create_access_token(user.id, user.username)
        response = await api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["display_name"] == "测试用户"

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, api_client):
        # 确保没有 dependency override
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides.pop(get_current_active_user, None)

        response = await api_client.get("/api/v1/auth/me")

        # FastAPI OAuth2PasswordBearer 返回 401 或 403 when missing token
        assert response.status_code in (401, 403)
