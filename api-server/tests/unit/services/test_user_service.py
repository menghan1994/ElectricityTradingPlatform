"""UserService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError
from app.models.user import UserRole
from app.schemas.user import AdminUserCreate, UserUpdate
from app.services.user_service import UserService, generate_temp_password

# 预计算的 bcrypt 哈希，避免每次调用 _make_user 时执行昂贵的 bcrypt rounds
# 对应明文: "Test@1234"
_PREHASHED_PASSWORD = "$2b$14$M2QxULsVAV.uRyUo18yo8ePtCWkB5WxXb.j8mXNi5CLqZWCsO1aAG"


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service():
    service = AsyncMock()
    return service


@pytest.fixture
def user_service(mock_user_repo, mock_audit_service):
    return UserService(mock_user_repo, mock_audit_service)


def _make_user(
    username: str = "testuser",
    role: str = "trader",
    is_active: bool = True,
):
    user = MagicMock()
    user.id = uuid4()
    user.username = username
    user.hashed_password = _PREHASHED_PASSWORD
    user.display_name = "测试用户"
    user.phone = "13800138000"
    user.email = None
    user.role = role
    user.is_active = is_active
    user.is_locked = False
    return user


def _make_admin():
    return _make_user(username="admin", role="admin")


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.create.side_effect = lambda u: u

        data = AdminUserCreate(
            username="newuser",
            display_name="新用户",
            phone="13900139000",
            role="trader",
        )
        user, temp_password = await user_service.create_user(admin, data)

        assert user.username == "newuser"
        assert user.role == "trader"
        assert temp_password
        assert len(temp_password) == 12
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_username.return_value = _make_user()

        data = AdminUserCreate(username="testuser")
        with pytest.raises(BusinessError) as exc_info:
            await user_service.create_user(admin, data)

        assert exc_info.value.code == "USERNAME_EXISTS"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.get_by_email.return_value = _make_user()

        data = AdminUserCreate(
            username="newuser",
            email="existing@example.com",
            role="trader",
        )
        with pytest.raises(BusinessError) as exc_info:
            await user_service.create_user(admin, data)

        assert exc_info.value.code == "EMAIL_EXISTS"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_user_no_email_skips_check(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.create.side_effect = lambda u: u
        # 如果 get_by_email 被错误调用，抛出异常以检测实现错误
        mock_user_repo.get_by_email.side_effect = RuntimeError("get_by_email should not be called when email is None")

        data = AdminUserCreate(username="newuser", role="trader")
        user, temp_password = await user_service.create_user(admin, data)

        assert user.username == "newuser"
        mock_user_repo.get_by_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_invalid_role_rejected_by_schema(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AdminUserCreate(username="newuser", role="invalid_role")

    @pytest.mark.asyncio
    async def test_create_user_invalid_role_via_service(self, user_service):
        """直接调用 service 传入无效 role（绕过 schema），验证运行时防御。"""
        admin = _make_admin()
        # 手动构造一个 AdminUserCreate-like 对象绕过 Pydantic 校验
        data = MagicMock()
        data.username = "newuser"
        data.display_name = "新用户"
        data.phone = None
        data.email = None
        data.role = "invalid_role"

        with pytest.raises(BusinessError) as exc_info:
            await user_service.create_user(admin, data)

        assert exc_info.value.code == "INVALID_ROLE"
        assert exc_info.value.status_code == 422


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user()
        mock_user_repo.get_by_id.return_value = target

        data = UserUpdate(display_name="新名字", phone="13700137000")
        result = await user_service.update_user(admin, target.id, data)

        assert result.display_name == "新名字"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, user_service, mock_user_repo):
        admin = _make_admin()
        target = _make_user()
        other_user = _make_user(username="other")
        mock_user_repo.get_by_id.return_value = target
        mock_user_repo.get_by_email.return_value = other_user

        data = UserUpdate(email="taken@example.com")
        with pytest.raises(BusinessError) as exc_info:
            await user_service.update_user(admin, target.id, data)

        assert exc_info.value.code == "EMAIL_EXISTS"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_user_same_email_no_conflict(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user()
        target.email = "same@example.com"
        mock_user_repo.get_by_id.return_value = target
        mock_user_repo.get_by_email.return_value = target

        data = UserUpdate(email="same@example.com")
        result = await user_service.update_user(admin, target.id, data)

        assert result == target
        mock_audit_service.log_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = None

        data = UserUpdate(display_name="新名字")
        with pytest.raises(BusinessError) as exc_info:
            await user_service.update_user(admin, uuid4(), data)

        assert exc_info.value.code == "USER_NOT_FOUND"


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_password_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user()
        mock_user_repo.get_by_id.return_value = target

        temp_password = await user_service.reset_password(admin, target.id)

        assert temp_password
        assert len(temp_password) == 12
        mock_user_repo.update_password.assert_called_once()
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await user_service.reset_password(admin, uuid4())

        assert exc_info.value.code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_admin_can_reset_own_password(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = admin

        temp_password = await user_service.reset_password(admin, admin.id)

        assert temp_password
        assert len(temp_password) == 12
        mock_user_repo.update_password.assert_called_once()
        mock_audit_service.log_action.assert_called_once()


class TestToggleActive:
    @pytest.mark.asyncio
    async def test_disable_user_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user()
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.toggle_active(admin, target.id, False)

        assert result.is_active is False
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable_user_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user(is_active=False)
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.toggle_active(admin, target.id, True)

        assert result.is_active is True
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_noop_when_same_state(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user(is_active=True)
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.toggle_active(admin, target.id, True)

        assert result.is_active is True
        mock_audit_service.log_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_disable_self_forbidden(self, user_service, mock_user_repo):
        admin = _make_admin()

        with pytest.raises(BusinessError) as exc_info:
            await user_service.toggle_active(admin, admin.id, False)

        assert exc_info.value.code == "CANNOT_MODIFY_SELF"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_toggle_user_not_found(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await user_service.toggle_active(admin, uuid4(), False)

        assert exc_info.value.code == "USER_NOT_FOUND"


class TestAssignRole:
    @pytest.mark.asyncio
    async def test_assign_role_success(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user()
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.assign_role(admin, target.id, "storage_operator")

        assert result.role == "storage_operator"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_invalid_role(self, user_service, mock_user_repo):
        admin = _make_admin()

        with pytest.raises(BusinessError) as exc_info:
            await user_service.assign_role(admin, uuid4(), "invalid_role")

        assert exc_info.value.code == "INVALID_ROLE"

    @pytest.mark.asyncio
    async def test_admin_cannot_demote_self(self, user_service, mock_user_repo):
        admin = _make_admin()

        with pytest.raises(BusinessError) as exc_info:
            await user_service.assign_role(admin, admin.id, "trader")

        assert exc_info.value.code == "CANNOT_MODIFY_SELF"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, user_service, mock_user_repo):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await user_service.assign_role(admin, uuid4(), "trader")

        assert exc_info.value.code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_assign_role_noop_when_same(self, user_service, mock_user_repo, mock_audit_service):
        admin = _make_admin()
        target = _make_user(role="trader")
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.assign_role(admin, target.id, "trader")

        assert result.role == "trader"
        mock_audit_service.log_action.assert_not_called()


class TestListUsers:
    @pytest.mark.asyncio
    async def test_list_users_success(self, user_service, mock_user_repo):
        users = [_make_user(f"user{i}") for i in range(3)]
        mock_user_repo.get_all_paginated.return_value = (users, 3)

        result_users, total = await user_service.list_users(1, 20)

        assert len(result_users) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_list_users_with_search(self, user_service, mock_user_repo):
        mock_user_repo.get_all_paginated.return_value = ([], 0)

        result_users, total = await user_service.list_users(1, 20, "nonexistent")

        assert len(result_users) == 0
        assert total == 0
        mock_user_repo.get_all_paginated.assert_called_once_with(1, 20, "nonexistent")


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self, user_service, mock_user_repo):
        target = _make_user()
        mock_user_repo.get_by_id.return_value = target

        result = await user_service.get_user(target.id)

        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service, mock_user_repo):
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await user_service.get_user(uuid4())

        assert exc_info.value.code == "USER_NOT_FOUND"


class TestGenerateTempPassword:
    def test_temp_password_length(self):
        pwd = generate_temp_password()
        assert len(pwd) == 12

    def test_temp_password_has_uppercase(self):
        pwd = generate_temp_password()
        assert any(c.isupper() for c in pwd)

    def test_temp_password_has_lowercase(self):
        pwd = generate_temp_password()
        assert any(c.islower() for c in pwd)

    def test_temp_password_has_digit(self):
        pwd = generate_temp_password()
        assert any(c.isdigit() for c in pwd)

    def test_temp_password_has_special(self):
        pwd = generate_temp_password()
        assert any(c in "!@#$%^&*" for c in pwd)
