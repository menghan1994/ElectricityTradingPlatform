"""AuditService 单元测试 — Mock Repository 依赖。"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.audit_service import AuditService


@pytest.fixture
def mock_audit_repo():
    repo = AsyncMock()
    repo.create.side_effect = lambda entity: entity
    return repo


@pytest.fixture
def audit_service(mock_audit_repo):
    return AuditService(mock_audit_repo)


class TestLogAction:
    @pytest.mark.asyncio
    async def test_log_action_creates_entry(self, audit_service, mock_audit_repo):
        user_id = uuid4()
        resource_id = uuid4()

        result = await audit_service.log_action(
            user_id=user_id,
            action="create_user",
            resource_type="user",
            resource_id=resource_id,
            changes_after={"username": "newuser"},
            ip_address="127.0.0.1",
        )

        mock_audit_repo.create.assert_called_once()
        created_entry = mock_audit_repo.create.call_args[0][0]
        assert created_entry.user_id == user_id
        assert created_entry.action == "create_user"
        assert created_entry.resource_type == "user"
        assert created_entry.resource_id == resource_id
        assert created_entry.changes_after == {"username": "newuser"}
        assert created_entry.ip_address == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_log_action_with_before_after(self, audit_service, mock_audit_repo):
        result = await audit_service.log_action(
            user_id=uuid4(),
            action="assign_role",
            resource_type="user",
            resource_id=uuid4(),
            changes_before={"role": "trader"},
            changes_after={"role": "admin"},
        )

        created_entry = mock_audit_repo.create.call_args[0][0]
        assert created_entry.changes_before == {"role": "trader"}
        assert created_entry.changes_after == {"role": "admin"}

    @pytest.mark.asyncio
    async def test_log_action_no_ip(self, audit_service, mock_audit_repo):
        result = await audit_service.log_action(
            user_id=uuid4(),
            action="reset_password",
            resource_type="user",
            resource_id=uuid4(),
        )

        created_entry = mock_audit_repo.create.call_args[0][0]
        assert created_entry.ip_address is None
        assert created_entry.changes_before is None
        assert created_entry.changes_after is None
