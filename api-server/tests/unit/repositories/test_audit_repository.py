"""AuditLogRepository 单元测试 — Mock 数据库会话。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def audit_repo(mock_session):
    return AuditLogRepository(mock_session)


class TestGetByResource:
    @pytest.mark.asyncio
    async def test_get_by_resource_returns_results(self, audit_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(spec=AuditLog)]
        mock_session.execute.return_value = mock_result

        results = await audit_repo.get_by_resource("user", uuid4())

        assert len(results) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_resource_empty(self, audit_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await audit_repo.get_by_resource("user", uuid4())

        assert len(results) == 0


class TestGetByUser:
    @pytest.mark.asyncio
    async def test_get_by_user_returns_results(self, audit_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(spec=AuditLog), MagicMock(spec=AuditLog)]
        mock_session.execute.return_value = mock_result

        results = await audit_repo.get_by_user(uuid4())

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_by_user_with_pagination(self, audit_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await audit_repo.get_by_user(uuid4(), skip=10, limit=5)

        assert len(results) == 0
        mock_session.execute.assert_called_once()
