"""DataAccessContext 单元测试 — 验证各角色的数据访问策略。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.data_access import (
    DataAccessContext,
    get_data_access_context,
    require_write_permission,
)
from app.core.exceptions import BusinessError
from app.models.user import UserRole
from app.schemas.user import RoleType


class TestDataAccessContext:
    def test_admin_has_full_access(self):
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.ADMIN,
            station_ids=None, device_ids=None,
        )
        assert ctx.has_full_station_access is True
        assert ctx.has_full_device_access is True
        assert ctx.is_readonly is False

    def test_trading_manager_has_full_access(self):
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.TRADING_MANAGER,
            station_ids=None, device_ids=None,
        )
        assert ctx.has_full_station_access is True
        assert ctx.has_full_device_access is True
        assert ctx.is_readonly is False

    def test_executive_readonly_full_access_but_readonly(self):
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.EXECUTIVE_READONLY,
            station_ids=None, device_ids=None,
        )
        assert ctx.has_full_station_access is True
        assert ctx.has_full_device_access is True
        assert ctx.is_readonly is True

    def test_trader_restricted_stations(self):
        station_ids = (uuid4(), uuid4())
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.TRADER,
            station_ids=station_ids, device_ids=None,
        )
        assert ctx.has_full_station_access is False
        assert ctx.station_ids == station_ids
        assert ctx.is_readonly is False

    def test_trader_no_bindings_empty_tuple(self):
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.TRADER,
            station_ids=(), device_ids=None,
        )
        assert ctx.has_full_station_access is False
        assert ctx.station_ids == ()

    def test_storage_operator_restricted_devices_and_stations(self):
        device_ids = (uuid4(),)
        station_ids = (uuid4(),)
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.STORAGE_OPERATOR,
            station_ids=station_ids, device_ids=device_ids,
        )
        assert ctx.has_full_station_access is False
        assert ctx.has_full_device_access is False
        assert ctx.station_ids == station_ids
        assert ctx.device_ids == device_ids
        assert ctx.is_readonly is False

    def test_tuple_immutability(self):
        """tuple 字段不能被 append/extend 修改，确保安全性"""
        station_ids = (uuid4(),)
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.TRADER,
            station_ids=station_ids, device_ids=None,
        )
        with pytest.raises(AttributeError):
            ctx.station_ids.append(uuid4())  # type: ignore[union-attr]

    def test_frozen_dataclass(self):
        ctx = DataAccessContext(
            user_id=uuid4(), role=UserRole.ADMIN,
            station_ids=None, device_ids=None,
        )
        with pytest.raises(AttributeError):
            ctx.role = "trader"


class TestGetDataAccessContext:
    def _make_user(self, role: RoleType):
        user = MagicMock()
        user.id = uuid4()
        user.role = role
        user.is_active = True
        user.is_locked = False
        return user

    @pytest.mark.asyncio
    async def test_admin_gets_full_access(self):
        user = self._make_user(UserRole.ADMIN)
        session = AsyncMock()
        ctx = await get_data_access_context(user, session)
        assert ctx.station_ids is None
        assert ctx.device_ids is None
        assert ctx.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_trading_manager_gets_full_access(self):
        user = self._make_user(UserRole.TRADING_MANAGER)
        session = AsyncMock()
        ctx = await get_data_access_context(user, session)
        assert ctx.station_ids is None
        assert ctx.device_ids is None

    @pytest.mark.asyncio
    async def test_executive_readonly_gets_full_access(self):
        user = self._make_user(UserRole.EXECUTIVE_READONLY)
        session = AsyncMock()
        ctx = await get_data_access_context(user, session)
        assert ctx.station_ids is None
        assert ctx.device_ids is None
        assert ctx.is_readonly is True

    @pytest.mark.asyncio
    async def test_trader_gets_bound_station_ids_as_tuple(self):
        user = self._make_user(UserRole.TRADER)
        session = AsyncMock()
        bound_ids = [uuid4(), uuid4()]

        # Mock BindingRepository.get_user_station_ids
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = bound_ids
        session.execute.return_value = mock_result

        ctx = await get_data_access_context(user, session)
        assert ctx.role == UserRole.TRADER
        assert ctx.station_ids == tuple(bound_ids)
        assert isinstance(ctx.station_ids, tuple)
        assert ctx.device_ids is None

    @pytest.mark.asyncio
    async def test_trader_no_bindings_gets_empty_tuple(self):
        user = self._make_user(UserRole.TRADER)
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        ctx = await get_data_access_context(user, session)
        assert ctx.station_ids == ()
        assert isinstance(ctx.station_ids, tuple)

    @pytest.mark.asyncio
    async def test_storage_operator_gets_bound_ids_as_tuples(self):
        user = self._make_user(UserRole.STORAGE_OPERATOR)
        session = AsyncMock()
        bound_device_ids = [uuid4()]
        bound_station_ids = [uuid4()]

        # 第一次调用: get_user_device_ids → 返回设备 ID
        device_result = MagicMock()
        device_result.scalars.return_value.all.return_value = bound_device_ids
        # 第二次调用: get_user_device_station_ids → 返回电站 ID
        station_result = MagicMock()
        station_result.scalars.return_value.all.return_value = bound_station_ids
        session.execute.side_effect = [device_result, station_result]

        ctx = await get_data_access_context(user, session)
        assert ctx.role == UserRole.STORAGE_OPERATOR
        assert ctx.device_ids == tuple(bound_device_ids)
        assert ctx.station_ids == tuple(bound_station_ids)
        assert isinstance(ctx.device_ids, tuple)
        assert isinstance(ctx.station_ids, tuple)


class TestRequireWritePermission:
    def _make_user(self, role: RoleType):
        user = MagicMock()
        user.id = uuid4()
        user.role = role
        user.is_active = True
        user.is_locked = False
        return user

    @pytest.mark.asyncio
    async def test_admin_can_write(self):
        user = self._make_user(UserRole.ADMIN)
        result = await require_write_permission(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_trader_can_write(self):
        user = self._make_user(UserRole.TRADER)
        result = await require_write_permission(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_trading_manager_can_write(self):
        user = self._make_user(UserRole.TRADING_MANAGER)
        result = await require_write_permission(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_storage_operator_can_write(self):
        user = self._make_user(UserRole.STORAGE_OPERATOR)
        result = await require_write_permission(user)
        assert result is user

    @pytest.mark.asyncio
    async def test_executive_readonly_cannot_write(self):
        user = self._make_user(UserRole.EXECUTIVE_READONLY)
        with pytest.raises(BusinessError) as exc_info:
            await require_write_permission(user)
        assert exc_info.value.code == "WRITE_PERMISSION_DENIED"
        assert exc_info.value.status_code == 403
