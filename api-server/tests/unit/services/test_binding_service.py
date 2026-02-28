"""BindingService 单元测试 — 角色校验、批量更新、审计日志。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.services.binding_service import BindingService


@pytest.fixture
def mock_binding_repo():
    return AsyncMock()


@pytest.fixture
def mock_station_repo():
    return AsyncMock()


@pytest.fixture
def mock_storage_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def binding_service(mock_binding_repo, mock_station_repo, mock_storage_repo, mock_user_repo, mock_audit_service):
    return BindingService(mock_binding_repo, mock_station_repo, mock_storage_repo, mock_user_repo, mock_audit_service)


def _make_user(role: str = "trader", is_active: bool = True, is_locked: bool = False):
    user = MagicMock()
    user.id = uuid4()
    user.username = f"test_{role}"
    user.role = role
    user.is_active = is_active
    user.is_locked = is_locked
    return user


def _make_admin():
    return _make_user(role="admin")


def _make_station(is_active: bool = True):
    station = MagicMock(spec=PowerStation)
    station.id = uuid4()
    station.name = "测试电站"
    station.is_active = is_active
    return station


def _make_device(is_active: bool = True):
    device = MagicMock(spec=StorageDevice)
    device.id = uuid4()
    device.name = "测试设备"
    device.is_active = is_active
    return device


class TestUpdateUserStationBindings:
    @pytest.mark.asyncio
    async def test_success_for_trader(
        self, binding_service, mock_user_repo, mock_station_repo, mock_binding_repo, mock_audit_service,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        stations = [_make_station(), _make_station()]
        station_ids = [s.id for s in stations]

        mock_user_repo.get_by_id.return_value = trader
        mock_station_repo.get_by_ids.return_value = stations
        mock_binding_repo.get_user_station_ids.return_value = []

        result_ids, result_stations = await binding_service.update_user_station_bindings(
            admin, trader.id, station_ids, "192.168.1.1",
        )

        assert result_ids == [s.id for s in stations]
        mock_binding_repo.replace_user_station_bindings.assert_called_once_with(trader.id, station_ids)
        mock_audit_service.log_action.assert_called_once()
        mock_station_repo.get_by_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_non_trader_role(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        non_trader = _make_user(role="storage_operator")
        mock_user_repo.get_by_id.return_value = non_trader

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, non_trader.id, [uuid4()])

        assert exc_info.value.code == "ROLE_BINDING_MISMATCH"
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_admin_role(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        admin_target = _make_user(role="admin")
        mock_user_repo.get_by_id.return_value = admin_target

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, admin_target.id, [uuid4()])

        assert exc_info.value.code == "ROLE_BINDING_MISMATCH"

    @pytest.mark.asyncio
    async def test_rejects_nonexistent_station(
        self, binding_service, mock_user_repo, mock_station_repo,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        mock_user_repo.get_by_id.return_value = trader

        missing_id = uuid4()
        mock_station_repo.get_by_ids.return_value = []  # None found

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, trader.id, [missing_id])

        assert exc_info.value.code == "STATION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_inactive_station(
        self, binding_service, mock_user_repo, mock_station_repo,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        inactive_station = _make_station(is_active=False)
        mock_user_repo.get_by_id.return_value = trader
        mock_station_repo.get_by_ids.return_value = [inactive_station]

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(
                admin, trader.id, [inactive_station.id],
            )

        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_not_found(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, uuid4(), [])

        assert exc_info.value.code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_empty_station_list_clears_bindings(
        self, binding_service, mock_user_repo, mock_binding_repo, mock_station_repo, mock_audit_service,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        mock_user_repo.get_by_id.return_value = trader
        mock_binding_repo.get_user_station_ids.return_value = [uuid4()]

        await binding_service.update_user_station_bindings(admin, trader.id, [], "192.168.1.1")

        mock_binding_repo.replace_user_station_bindings.assert_called_once_with(trader.id, [])
        mock_audit_service.log_action.assert_called_once()


class TestUpdateUserDeviceBindings:
    @pytest.mark.asyncio
    async def test_success_for_operator(
        self, binding_service, mock_user_repo, mock_storage_repo, mock_binding_repo, mock_audit_service,
    ):
        admin = _make_admin()
        operator = _make_user(role="storage_operator")
        devices = [_make_device()]
        device_ids = [d.id for d in devices]

        mock_user_repo.get_by_id.return_value = operator
        mock_storage_repo.get_by_ids.return_value = devices
        mock_binding_repo.get_user_device_ids.return_value = []

        result_ids, result_devices = await binding_service.update_user_device_bindings(
            admin, operator.id, device_ids, "192.168.1.1",
        )

        assert result_ids == [d.id for d in devices]
        mock_binding_repo.replace_user_device_bindings.assert_called_once()
        mock_audit_service.log_action.assert_called_once()
        mock_storage_repo.get_by_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_non_operator_role(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        mock_user_repo.get_by_id.return_value = trader

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_device_bindings(admin, trader.id, [uuid4()])

        assert exc_info.value.code == "ROLE_BINDING_MISMATCH"
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_nonexistent_device(
        self, binding_service, mock_user_repo, mock_storage_repo,
    ):
        admin = _make_admin()
        operator = _make_user(role="storage_operator")
        mock_user_repo.get_by_id.return_value = operator
        mock_storage_repo.get_by_ids.return_value = []

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_device_bindings(admin, operator.id, [uuid4()])

        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_rejects_inactive_device(
        self, binding_service, mock_user_repo, mock_storage_repo,
    ):
        admin = _make_admin()
        operator = _make_user(role="storage_operator")
        inactive_device = _make_device(is_active=False)
        mock_user_repo.get_by_id.return_value = operator
        mock_storage_repo.get_by_ids.return_value = [inactive_device]

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_device_bindings(
                admin, operator.id, [inactive_device.id],
            )

        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_deduplicates_device_ids(
        self, binding_service, mock_user_repo, mock_storage_repo, mock_binding_repo, mock_audit_service,
    ):
        admin = _make_admin()
        operator = _make_user(role="storage_operator")
        device = _make_device()

        mock_user_repo.get_by_id.return_value = operator
        mock_storage_repo.get_by_ids.return_value = [device]
        mock_binding_repo.get_user_device_ids.return_value = []

        # Pass duplicate IDs
        await binding_service.update_user_device_bindings(
            admin, operator.id, [device.id, device.id, device.id], "192.168.1.1",
        )

        # Verify only deduplicated list is passed to replace
        mock_binding_repo.replace_user_device_bindings.assert_called_once_with(
            operator.id, [device.id],
        )


class TestDeduplicateStationIds:
    @pytest.mark.asyncio
    async def test_deduplicates_station_ids(
        self, binding_service, mock_user_repo, mock_station_repo, mock_binding_repo, mock_audit_service,
    ):
        admin = _make_admin()
        trader = _make_user(role="trader")
        station = _make_station()

        mock_user_repo.get_by_id.return_value = trader
        mock_station_repo.get_by_ids.return_value = [station]
        mock_binding_repo.get_user_station_ids.return_value = []

        # Pass duplicate IDs
        await binding_service.update_user_station_bindings(
            admin, trader.id, [station.id, station.id, station.id], "192.168.1.1",
        )

        # Verify only deduplicated list is passed to replace
        mock_binding_repo.replace_user_station_bindings.assert_called_once_with(
            trader.id, [station.id],
        )


class TestGetUserStationBindings:
    @pytest.mark.asyncio
    async def test_returns_ids_and_stations(
        self, binding_service, mock_binding_repo, mock_station_repo, mock_user_repo,
    ):
        user = _make_user(role="trader")
        stations = [_make_station(), _make_station()]
        station_ids = [uuid4(), uuid4()]

        mock_user_repo.get_by_id.return_value = user
        mock_binding_repo.get_user_station_ids.return_value = station_ids
        mock_station_repo.get_by_ids.return_value = stations

        result_ids, result_stations = await binding_service.get_user_station_bindings(user.id)

        # active_ids are derived from returned stations
        assert result_ids == [s.id for s in stations]
        assert len(result_stations) == 2
        mock_station_repo.get_by_ids.assert_called_once_with(station_ids, active_only=True)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_bindings(
        self, binding_service, mock_binding_repo, mock_station_repo, mock_user_repo,
    ):
        user = _make_user(role="trader")
        mock_user_repo.get_by_id.return_value = user
        mock_binding_repo.get_user_station_ids.return_value = []

        result_ids, result_stations = await binding_service.get_user_station_bindings(user.id)

        assert result_ids == []
        assert result_stations == []
        mock_station_repo.get_by_ids.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_user(
        self, binding_service, mock_user_repo,
    ):
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.get_user_station_bindings(uuid4())

        assert exc_info.value.code == "USER_NOT_FOUND"


class TestGetUserDeviceBindings:
    @pytest.mark.asyncio
    async def test_returns_ids_and_devices(
        self, binding_service, mock_binding_repo, mock_storage_repo, mock_user_repo,
    ):
        user = _make_user(role="storage_operator")
        devices = [_make_device(), _make_device()]
        device_ids = [uuid4(), uuid4()]

        mock_user_repo.get_by_id.return_value = user
        mock_binding_repo.get_user_device_ids.return_value = device_ids
        mock_storage_repo.get_by_ids.return_value = devices

        result_ids, result_devices = await binding_service.get_user_device_bindings(user.id)

        assert result_ids == [d.id for d in devices]
        assert len(result_devices) == 2
        mock_storage_repo.get_by_ids.assert_called_once_with(device_ids, active_only=True)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_bindings(
        self, binding_service, mock_binding_repo, mock_storage_repo, mock_user_repo,
    ):
        user = _make_user(role="storage_operator")
        mock_user_repo.get_by_id.return_value = user
        mock_binding_repo.get_user_device_ids.return_value = []

        result_ids, result_devices = await binding_service.get_user_device_bindings(user.id)

        assert result_ids == []
        assert result_devices == []
        mock_storage_repo.get_by_ids.assert_not_called()


class TestValidateUserStatus:
    @pytest.mark.asyncio
    async def test_rejects_inactive_user_for_station_binding(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        inactive = _make_user(role="trader", is_active=False)
        mock_user_repo.get_by_id.return_value = inactive

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, inactive.id, [])

        assert exc_info.value.code == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_rejects_locked_user_for_station_binding(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        locked = _make_user(role="trader", is_locked=True)
        mock_user_repo.get_by_id.return_value = locked

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_station_bindings(admin, locked.id, [])

        assert exc_info.value.code == "USER_LOCKED"

    @pytest.mark.asyncio
    async def test_rejects_inactive_user_for_device_binding(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        inactive = _make_user(role="storage_operator", is_active=False)
        mock_user_repo.get_by_id.return_value = inactive

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_device_bindings(admin, inactive.id, [])

        assert exc_info.value.code == "USER_INACTIVE"

    @pytest.mark.asyncio
    async def test_rejects_locked_user_for_device_binding(
        self, binding_service, mock_user_repo,
    ):
        admin = _make_admin()
        locked = _make_user(role="storage_operator", is_locked=True)
        mock_user_repo.get_by_id.return_value = locked

        with pytest.raises(BusinessError) as exc_info:
            await binding_service.update_user_device_bindings(admin, locked.id, [])

        assert exc_info.value.code == "USER_LOCKED"
