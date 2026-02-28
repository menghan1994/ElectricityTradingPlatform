"""BindingRepository 单元测试 — Mock 数据库会话，验证绑定操作。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.binding import UserDeviceBinding, UserStationBinding
from app.repositories.binding import BindingRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def binding_repo(mock_session):
    return BindingRepository(mock_session)


class TestGetUserStationBindings:
    @pytest.mark.asyncio
    async def test_returns_bindings(self, binding_repo, mock_session):
        binding1 = MagicMock(spec=UserStationBinding)
        binding2 = MagicMock(spec=UserStationBinding)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [binding1, binding2]
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_user_station_bindings(uuid4())

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_bindings(self, binding_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_user_station_bindings(uuid4())

        assert result == []


class TestGetUserStationIds:
    @pytest.mark.asyncio
    async def test_returns_station_ids(self, binding_repo, mock_session):
        station_ids = [uuid4(), uuid4()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = station_ids
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_user_station_ids(uuid4())

        assert len(result) == 2


class TestReplaceUserStationBindings:
    @pytest.mark.asyncio
    async def test_replaces_bindings(self, binding_repo, mock_session):
        user_id = uuid4()
        station_ids = [uuid4(), uuid4()]

        result = await binding_repo.replace_user_station_bindings(user_id, station_ids)

        # Verify old bindings were deleted
        mock_session.execute.assert_called_once()
        # Verify new bindings were added
        assert mock_session.add.call_count == 2
        # Verify flush was called
        mock_session.flush.assert_called_once()
        assert len(result) == 2
        # Verify binding objects have correct attributes
        for binding in result:
            assert isinstance(binding, UserStationBinding)
            assert binding.user_id == user_id

    @pytest.mark.asyncio
    async def test_replaces_with_empty_list(self, binding_repo, mock_session):
        user_id = uuid4()

        result = await binding_repo.replace_user_station_bindings(user_id, [])

        mock_session.execute.assert_called_once()
        mock_session.add.assert_not_called()
        assert len(result) == 0


class TestGetUserDeviceIds:
    @pytest.mark.asyncio
    async def test_returns_device_ids(self, binding_repo, mock_session):
        device_ids = [uuid4(), uuid4()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = device_ids
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_user_device_ids(uuid4())

        assert len(result) == 2


class TestGetUserDeviceBindings:
    @pytest.mark.asyncio
    async def test_returns_device_bindings(self, binding_repo, mock_session):
        binding1 = MagicMock(spec=UserDeviceBinding)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [binding1]
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_user_device_bindings(uuid4())

        assert len(result) == 1


class TestReplaceUserDeviceBindings:
    @pytest.mark.asyncio
    async def test_replaces_device_bindings(self, binding_repo, mock_session):
        user_id = uuid4()
        device_ids = [uuid4()]

        result = await binding_repo.replace_user_device_bindings(user_id, device_ids)

        mock_session.execute.assert_called_once()
        assert mock_session.add.call_count == 1
        mock_session.flush.assert_called_once()
        assert len(result) == 1


class TestGetStationBindingCount:
    @pytest.mark.asyncio
    async def test_returns_count(self, binding_repo, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await binding_repo.get_station_binding_count(uuid4())

        assert result == 5
