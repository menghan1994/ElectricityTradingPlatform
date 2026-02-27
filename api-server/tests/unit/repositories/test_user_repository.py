"""UserRepository 单元测试 — Mock 数据库会话，验证 Repository 操作。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.user import User
from app.repositories.user import UserRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def user_repo(mock_session):
    return UserRepository(mock_session)


def _make_user(**kwargs):
    defaults = {
        "id": uuid4(),
        "username": "testuser",
        "hashed_password": "$2b$14$fakehash",
        "display_name": "Test",
        "phone": None,
        "is_active": True,
        "is_locked": False,
        "locked_until": None,
        "failed_login_attempts": 0,
        "last_login_at": None,
    }
    defaults.update(kwargs)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


class TestGetByUsername:
    @pytest.mark.asyncio
    async def test_returns_user_when_found(self, user_repo, mock_session):
        user = _make_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        result = await user_repo.get_by_username("testuser")

        assert result is user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, user_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await user_repo.get_by_username("nonexistent")

        assert result is None


class TestIncrementFailedAttempts:
    @pytest.mark.asyncio
    async def test_increments_counter(self, user_repo, mock_session):
        user = _make_user(failed_login_attempts=2)

        await user_repo.increment_failed_attempts(user)

        assert user.failed_login_attempts == 3
        mock_session.flush.assert_called_once()


class TestResetFailedAttempts:
    @pytest.mark.asyncio
    async def test_resets_all_lock_fields(self, user_repo, mock_session):
        user = _make_user(
            failed_login_attempts=5,
            is_locked=True,
            locked_until=datetime.now(UTC) + timedelta(minutes=10),
        )

        await user_repo.reset_failed_attempts(user)

        assert user.failed_login_attempts == 0
        assert user.is_locked is False
        assert user.locked_until is None
        mock_session.flush.assert_called_once()


class TestLockAccount:
    @pytest.mark.asyncio
    async def test_locks_account(self, user_repo, mock_session):
        user = _make_user()

        await user_repo.lock_account(user, lock_minutes=15)

        assert user.is_locked is True
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(UTC)
        mock_session.flush.assert_called_once()


class TestUpdateLastLogin:
    @pytest.mark.asyncio
    async def test_updates_last_login(self, user_repo, mock_session):
        user = _make_user()

        await user_repo.update_last_login(user)

        assert user.last_login_at is not None
        mock_session.flush.assert_called_once()


class TestUpdatePassword:
    @pytest.mark.asyncio
    async def test_updates_password_hash(self, user_repo, mock_session):
        user = _make_user()
        new_hash = "$2b$14$newhash"

        await user_repo.update_password(user, new_hash)

        assert user.hashed_password == new_hash
        mock_session.flush.assert_called_once()
