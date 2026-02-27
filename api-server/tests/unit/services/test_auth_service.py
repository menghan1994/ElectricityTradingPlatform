"""AuthService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.services.auth_service import AuthService, LOCK_MINUTES, MAX_FAILED_ATTEMPTS

# 预计算的 bcrypt 哈希常量，避免每次 _make_user 时执行昂贵的 bcrypt rounds=14
# 对应明文: "Test@1234"
_PREHASHED_TEST = "$2b$14$M2QxULsVAV.uRyUo18yo8ePtCWkB5WxXb.j8mXNi5CLqZWCsO1aAG"
# 对应明文: "OldPass@123"（change_password 测试专用）
_PREHASHED_OLDPASS = hash_password("OldPass@123")

# 预计算哈希映射：避免在测试中重复调用 bcrypt
_PASSWORD_HASHES: dict[str, str] = {
    "Test@1234": _PREHASHED_TEST,
    "OldPass@123": _PREHASHED_OLDPASS,
}


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def auth_service(mock_user_repo):
    return AuthService(mock_user_repo)


def _make_user(
    username: str = "testuser",
    password: str = "Test@1234",
    is_active: bool = True,
    is_locked: bool = False,
    locked_until: datetime | None = None,
    failed_login_attempts: int = 0,
    role: str = "trader",
):
    user = MagicMock()
    user.id = uuid4()
    user.username = username
    user.hashed_password = _PASSWORD_HASHES.get(password) or hash_password(password)
    user.is_active = is_active
    user.is_locked = is_locked
    user.locked_until = locked_until
    user.failed_login_attempts = failed_login_attempts
    user.role = role
    return user


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_user_repo):
        user = _make_user()
        mock_user_repo.get_by_username.return_value = user

        access_token, refresh_token = await auth_service.authenticate("testuser", "Test@1234")

        assert access_token
        assert refresh_token
        mock_user_repo.reset_failed_attempts.assert_called_once_with(user)
        mock_user_repo.update_last_login.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service, mock_user_repo):
        mock_user_repo.get_by_username.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.authenticate("nonexistent", "pass")

        assert exc_info.value.code == "INVALID_CREDENTIALS"
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service, mock_user_repo):
        user = _make_user()
        mock_user_repo.get_by_username.return_value = user

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.authenticate("testuser", "WrongPass1!")

        assert exc_info.value.code == "INVALID_CREDENTIALS"
        mock_user_repo.increment_failed_attempts.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_login_account_locked(self, auth_service, mock_user_repo):
        user = _make_user(
            is_locked=True,
            locked_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        mock_user_repo.get_by_username.return_value = user

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.authenticate("testuser", "Test@1234")

        assert exc_info.value.code == "ACCOUNT_LOCKED"
        assert exc_info.value.status_code == 403
        assert "remaining_minutes" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_lock_expired_auto_unlock(self, auth_service, mock_user_repo):
        user = _make_user(
            is_locked=True,
            locked_until=datetime.now(UTC) - timedelta(minutes=1),
        )
        mock_user_repo.get_by_username.return_value = user

        access_token, refresh_token = await auth_service.authenticate("testuser", "Test@1234")

        assert access_token
        assert refresh_token
        # 解锁应该被调用
        mock_user_repo.reset_failed_attempts.assert_called()

    @pytest.mark.asyncio
    async def test_login_triggers_lock_on_max_failures(self, auth_service, mock_user_repo):
        user = _make_user(failed_login_attempts=MAX_FAILED_ATTEMPTS - 1)
        mock_user_repo.get_by_username.return_value = user

        # Mock needs to simulate the side effect of incrementing the counter
        async def _increment(u):
            u.failed_login_attempts += 1
        mock_user_repo.increment_failed_attempts.side_effect = _increment

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.authenticate("testuser", "WrongPass1!")

        assert exc_info.value.code == "INVALID_CREDENTIALS"
        mock_user_repo.lock_account.assert_called_once_with(user, LOCK_MINUTES)

    @pytest.mark.asyncio
    async def test_login_account_disabled(self, auth_service, mock_user_repo):
        user = _make_user(is_active=False)
        mock_user_repo.get_by_username.return_value = user

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.authenticate("testuser", "Test@1234")

        assert exc_info.value.code == "ACCOUNT_DISABLED"
        assert exc_info.value.status_code == 403


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, mock_user_repo):
        user = _make_user(password="OldPass@123")
        mock_user_repo.get_by_id.return_value = user

        await auth_service.change_password(user.id, "OldPass@123", "NewPass@456")

        mock_user_repo.update_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, auth_service, mock_user_repo):
        user = _make_user(password="OldPass@123")
        mock_user_repo.get_by_id.return_value = user

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.change_password(user.id, "WrongOld@1", "NewPass@456")

        assert exc_info.value.code == "PASSWORD_MISMATCH"

    @pytest.mark.asyncio
    async def test_change_password_weak_new(self, auth_service, mock_user_repo):
        user = _make_user(password="OldPass@123")
        mock_user_repo.get_by_id.return_value = user

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.change_password(user.id, "OldPass@123", "weak")

        assert exc_info.value.code == "PASSWORD_TOO_WEAK"
        assert "violations" in exc_info.value.detail


class TestRefreshAccessToken:
    @pytest.mark.asyncio
    async def test_refresh_success(self, auth_service, mock_user_repo):
        from app.core.security import create_refresh_token

        user = _make_user()
        mock_user_repo.get_by_id.return_value = user
        refresh = create_refresh_token(user.id)

        new_access = await auth_service.refresh_access_token(refresh)

        assert new_access

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, auth_service, mock_user_repo):
        with pytest.raises(BusinessError) as exc_info:
            await auth_service.refresh_access_token("invalid.token.here")

        assert exc_info.value.code == "TOKEN_INVALID"

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_rejected(self, auth_service, mock_user_repo):
        from app.core.security import create_access_token

        user = _make_user()
        # 使用 access token 来刷新应该被拒绝
        access = create_access_token(user.id, user.username)

        with pytest.raises(BusinessError) as exc_info:
            await auth_service.refresh_access_token(access)

        assert exc_info.value.code == "TOKEN_INVALID"


class TestPasswordStrength:
    def test_strong_password_passes(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("Test@1234")
        assert violations == []

    def test_short_password_fails(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("T@1a")
        assert any("至少8" in v for v in violations)

    def test_no_uppercase_fails(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("test@1234")
        assert any("大写" in v for v in violations)

    def test_no_lowercase_fails(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("TEST@1234")
        assert any("小写" in v for v in violations)

    def test_no_digit_fails(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("Test@abcd")
        assert any("数字" in v for v in violations)

    def test_no_special_char_fails(self):
        from app.core.security import validate_password_strength
        violations = validate_password_strength("Test12345")
        assert any("特殊字符" in v for v in violations)
