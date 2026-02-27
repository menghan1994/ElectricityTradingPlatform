"""用户管理 API 端到端测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import BusinessError
from app.main import app
from app.models.user import User

# 预计算的 bcrypt 哈希，避免每次调用 _make_user_obj 时执行昂贵的 bcrypt rounds
# 对应明文: "Test@1234"
_PREHASHED_PASSWORD = "$2b$14$M2QxULsVAV.uRyUo18yo8ePtCWkB5WxXb.j8mXNi5CLqZWCsO1aAG"


def _make_user_obj(
    username: str = "testuser",
    role: str = "trader",
    is_active: bool = True,
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = username
    user.hashed_password = _PREHASHED_PASSWORD
    user.display_name = "测试用户"
    user.phone = "13800138000"
    user.email = None
    user.role = role
    user.is_active = is_active
    user.is_locked = False
    user.locked_until = None
    user.failed_login_attempts = 0
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_admin_obj() -> MagicMock:
    return _make_user_obj(username="admin", role="admin")


def _create_mock_user_service(users: list[MagicMock] | None = None):
    """创建一个 mock 的 UserService。"""
    from app.services.user_service import UserService

    service = AsyncMock(spec=UserService)

    if users is None:
        users = [_make_user_obj(f"user{i}") for i in range(3)]

    service.list_users.return_value = (users, len(users))
    service.get_user.return_value = users[0] if users else None
    service.create_user.return_value = (users[0] if users else _make_user_obj(), "TempPass@123")
    service.update_user.return_value = users[0] if users else None
    service.reset_password.return_value = "TempPass@456"
    service.toggle_active.return_value = users[0] if users else None
    service.assign_role.return_value = users[0] if users else None

    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestUsersListEndpoint:
    @pytest.mark.asyncio
    async def test_list_users_as_admin(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_users_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestGetUserEndpoint:
    @pytest.mark.asyncio
    async def test_get_user_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        user_id = str(uuid4())
        response = await api_client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestCreateUserEndpoint:
    @pytest.mark.asyncio
    async def test_create_user_as_admin(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/users",
            json={"username": "newuser", "display_name": "新用户", "role": "trader"},
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "temp_password" in data


    @pytest.mark.asyncio
    async def test_create_user_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.post(
            "/api/v1/users",
            json={"username": "newuser", "display_name": "新用户", "role": "trader"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestUpdateUserEndpoint:
    @pytest.mark.asyncio
    async def test_update_user_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        user_id = str(uuid4())
        response = await api_client.put(
            f"/api/v1/users/{user_id}",
            json={"display_name": "新名字"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestResetPasswordEndpoint:
    @pytest.mark.asyncio
    async def test_reset_password_as_admin(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        user_id = str(uuid4())
        response = await api_client.post(
            f"/api/v1/users/{user_id}/reset_password",
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 200
        assert "temp_password" in response.json()


    @pytest.mark.asyncio
    async def test_reset_password_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        user_id = str(uuid4())
        response = await api_client.post(
            f"/api/v1/users/{user_id}/reset_password",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestToggleStatusEndpoint:
    @pytest.mark.asyncio
    async def test_toggle_status_as_admin(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        user_id = str(uuid4())
        response = await api_client.put(
            f"/api/v1/users/{user_id}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 200


    @pytest.mark.asyncio
    async def test_toggle_status_forbidden_for_non_admin(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        user_id = str(uuid4())
        response = await api_client.put(
            f"/api/v1/users/{user_id}/status",
            json={"is_active": False},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestAssignRoleEndpoint:
    @pytest.mark.asyncio
    async def test_assign_role_as_admin(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        user_id = str(uuid4())
        response = await api_client.put(
            f"/api/v1/users/{user_id}/role",
            json={"role": "storage_operator"},
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_assign_role_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        user_id = str(uuid4())
        response = await api_client.put(
            f"/api/v1/users/{user_id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer fake"},
        )

        assert response.status_code == 403


class TestErrorPaths:
    """错误路径测试 — 409 重复、404 不存在、422 参数校验失败。"""

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username_409(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()
        mock_service.create_user.side_effect = BusinessError(
            code="USERNAME_EXISTS", message="用户名已被注册", status_code=409,
        )

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/users",
            json={"username": "existing", "role": "trader"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_get_user_not_found_404(self, api_client):
        admin = _make_admin_obj()
        mock_service = _create_mock_user_service()
        mock_service.get_user.side_effect = BusinessError(
            code="USER_NOT_FOUND", message="用户不存在", status_code=404,
        )

        from app.api.v1.users import _get_user_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_user_service] = lambda: mock_service

        user_id = str(uuid4())
        response = await api_client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 404
        assert response.json()["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_user_invalid_payload_422(self, api_client):
        admin = _make_admin_obj()

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin

        # username 过短（min_length=3）
        response = await api_client.post(
            "/api/v1/users",
            json={"username": "ab", "role": "trader"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422
