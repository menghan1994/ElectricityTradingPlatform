"""StationService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.data_access import DataAccessContext
from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.user import UserRole
from app.schemas.station import StationCreate, StationUpdate
from app.services.station_service import StationService


@pytest.fixture
def mock_station_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_storage_repo():
    return AsyncMock()


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def station_service(mock_station_repo, mock_audit_service, mock_storage_repo):
    return StationService(mock_station_repo, mock_audit_service, storage_repo=mock_storage_repo)


def _make_station(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "测试电站",
        "province": "guangdong",
        "capacity_mw": Decimal("100.00"),
        "station_type": "wind",
        "has_storage": False,
        "is_active": True,
    }
    defaults.update(kwargs)
    station = MagicMock(spec=PowerStation)
    for k, v in defaults.items():
        setattr(station, k, v)
    return station


def _make_admin():
    admin = MagicMock()
    admin.id = uuid4()
    admin.username = "admin"
    admin.role = "admin"
    return admin


class TestCreateStation:
    @pytest.mark.asyncio
    async def test_create_station_success(self, station_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.side_effect = lambda s: s

        data = StationCreate(
            name="新电站",
            province="shandong",
            capacity_mw=Decimal("50.00"),
            station_type="solar",
            has_storage=False,
        )
        result = await station_service.create_station(admin, data, "192.168.1.1")

        assert result.name == "新电站"
        assert result.province == "shandong"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_station_duplicate_name(self, station_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = _make_station()

        data = StationCreate(
            name="测试电站",
            province="guangdong",
            capacity_mw=Decimal("100.00"),
            station_type="wind",
        )

        with pytest.raises(BusinessError) as exc_info:
            await station_service.create_station(admin, data)

        assert exc_info.value.code == "STATION_NAME_DUPLICATE"
        assert exc_info.value.status_code == 409


class TestUpdateStation:
    @pytest.mark.asyncio
    async def test_update_station_success(self, station_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        data = StationUpdate(province="shandong")
        result = await station_service.update_station(admin, station.id, data, "192.168.1.1")

        assert station.province == "shandong"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_station_not_found(self, station_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_id.return_value = None

        data = StationUpdate(province="shandong")

        with pytest.raises(BusinessError) as exc_info:
            await station_service.update_station(admin, uuid4(), data)

        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_station_duplicate_name(self, station_service, mock_station_repo):
        admin = _make_admin()
        station = _make_station(name="电站A")
        mock_station_repo.get_by_id.return_value = station
        mock_station_repo.get_by_name.return_value = _make_station(name="电站B")

        data = StationUpdate(name="电站B")

        with pytest.raises(BusinessError) as exc_info:
            await station_service.update_station(admin, station.id, data)

        assert exc_info.value.code == "STATION_NAME_DUPLICATE"


class TestDeleteStation:
    @pytest.mark.asyncio
    async def test_delete_station_success(self, station_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station
        mock_station_repo.has_active_bindings.return_value = False

        await station_service.delete_station(admin, station.id, "192.168.1.1")

        assert station.is_active is False
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_station_not_found(self, station_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await station_service.delete_station(admin, uuid4())

        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_station_with_bindings(self, station_service, mock_station_repo):
        admin = _make_admin()
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station
        mock_station_repo.has_active_bindings.return_value = True

        with pytest.raises(BusinessError) as exc_info:
            await station_service.delete_station(admin, station.id)

        assert exc_info.value.code == "STATION_HAS_BINDINGS"
        assert exc_info.value.status_code == 409


    @pytest.mark.asyncio
    async def test_delete_already_deactivated_station_is_noop(self, station_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station(is_active=False)
        mock_station_repo.get_by_id.return_value = station

        await station_service.delete_station(admin, station.id, "192.168.1.1")

        mock_station_repo.has_active_bindings.assert_not_called()
        mock_audit_service.log_action.assert_not_called()


class TestUpdateStationDeactivate:
    @pytest.mark.asyncio
    async def test_update_station_deactivate_with_bindings_rejected(self, station_service, mock_station_repo):
        admin = _make_admin()
        station = _make_station(is_active=True)
        mock_station_repo.get_by_id.return_value = station
        mock_station_repo.has_active_bindings.return_value = True

        data = StationUpdate(is_active=False)

        with pytest.raises(BusinessError) as exc_info:
            await station_service.update_station(admin, station.id, data)

        assert exc_info.value.code == "STATION_HAS_BINDINGS"
        assert exc_info.value.status_code == 409


class TestGetStation:
    @pytest.mark.asyncio
    async def test_get_station_success(self, station_service, mock_station_repo):
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        result = await station_service.get_station(station.id)

        assert result is station

    @pytest.mark.asyncio
    async def test_get_station_not_found(self, station_service, mock_station_repo):
        mock_station_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await station_service.get_station(uuid4())

        assert exc_info.value.code == "STATION_NOT_FOUND"


class TestListStations:
    @pytest.mark.asyncio
    async def test_list_stations(self, station_service, mock_station_repo):
        stations = [_make_station(name=f"电站{i}") for i in range(3)]
        mock_station_repo.get_all_paginated.return_value = (stations, 3)

        result, total = await station_service.list_stations(page=1, page_size=20)

        assert len(result) == 3
        assert total == 3


class TestGetAllActiveStations:
    @pytest.mark.asyncio
    async def test_returns_active_stations(self, station_service, mock_station_repo):
        stations = [_make_station(name="电站A"), _make_station(name="电站B")]
        mock_station_repo.get_all_active.return_value = stations

        result = await station_service.get_all_active_stations()

        assert len(result) == 2
        mock_station_repo.get_all_active.assert_called_once()


class TestGetAllActiveDevices:
    @pytest.mark.asyncio
    async def test_returns_active_devices(self, station_service, mock_storage_repo):
        device = MagicMock()
        device.id = uuid4()
        mock_storage_repo.get_all_active.return_value = [device]

        result = await station_service.get_all_active_devices()

        assert len(result) == 1
        mock_storage_repo.get_all_active.assert_called_once()


class TestGetAllActiveDevicesWithStationNames:
    @pytest.mark.asyncio
    async def test_returns_devices_with_station_name_map(self, station_service, mock_storage_repo, mock_station_repo):
        station = _make_station(name="广东风电A")
        device = MagicMock()
        device.id = uuid4()
        device.station_id = station.id
        mock_storage_repo.get_all_active.return_value = [device]
        mock_station_repo.get_by_ids.return_value = [station]

        devices, name_map = await station_service.get_all_active_devices_with_station_names()

        assert len(devices) == 1
        assert name_map[str(station.id)] == "广东风电A"


# ── 数据访问控制方法测试（Story 1.5） ──


def _make_access_ctx(role: str = UserRole.ADMIN, station_ids=None, device_ids=None):
    return DataAccessContext(
        user_id=uuid4(), role=role,
        station_ids=tuple(station_ids) if station_ids is not None else None,
        device_ids=tuple(device_ids) if device_ids is not None else None,
    )


class TestListStationsForUser:
    @pytest.mark.asyncio
    async def test_admin_gets_all(self, station_service, mock_station_repo):
        stations = [_make_station(name=f"电站{i}") for i in range(3)]
        mock_station_repo.get_all_paginated_filtered.return_value = (stations, 3)

        ctx = _make_access_ctx(role=UserRole.ADMIN)
        result, total = await station_service.list_stations_for_user(ctx, page=1, page_size=20)

        assert len(result) == 3
        assert total == 3
        mock_station_repo.get_all_paginated_filtered.assert_called_once_with(
            allowed_station_ids=None, page=1, page_size=20,
            search=None, province=None, station_type=None, is_active=None,
        )

    @pytest.mark.asyncio
    async def test_trader_gets_filtered(self, station_service, mock_station_repo):
        sid = uuid4()
        stations = [_make_station(id=sid)]
        mock_station_repo.get_all_paginated_filtered.return_value = (stations, 1)

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=[sid])
        result, total = await station_service.list_stations_for_user(ctx, page=1, page_size=20)

        assert total == 1
        mock_station_repo.get_all_paginated_filtered.assert_called_once_with(
            allowed_station_ids=(sid,), page=1, page_size=20,
            search=None, province=None, station_type=None, is_active=None,
        )

    @pytest.mark.asyncio
    async def test_trader_no_bindings_gets_empty(self, station_service, mock_station_repo):
        mock_station_repo.get_all_paginated_filtered.return_value = ([], 0)

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=())
        result, total = await station_service.list_stations_for_user(ctx, page=1, page_size=20)

        assert result == []
        assert total == 0


class TestGetStationForUser:
    @pytest.mark.asyncio
    async def test_admin_access(self, station_service, mock_station_repo):
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        ctx = _make_access_ctx(role=UserRole.ADMIN)
        result = await station_service.get_station_for_user(ctx, station.id)

        assert result is station

    @pytest.mark.asyncio
    async def test_station_not_found_returns_404(self, station_service, mock_station_repo):
        """电站不存在时返回 404，而非 403"""
        mock_station_repo.get_by_id.return_value = None

        ctx = _make_access_ctx(role=UserRole.ADMIN)

        with pytest.raises(BusinessError) as exc_info:
            await station_service.get_station_for_user(ctx, uuid4())

        assert exc_info.value.code == "STATION_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_trader_access_denied(self, station_service, mock_station_repo):
        """电站存在但 trader 无权访问时返回 403"""
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=(uuid4(),))

        with pytest.raises(BusinessError) as exc_info:
            await station_service.get_station_for_user(ctx, station.id)

        assert exc_info.value.code == "STATION_ACCESS_DENIED"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_trader_access_allowed(self, station_service, mock_station_repo):
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=(station.id,))
        result = await station_service.get_station_for_user(ctx, station.id)

        assert result is station


class TestGetAllActiveStationsForUser:
    @pytest.mark.asyncio
    async def test_admin_full_access(self, station_service, mock_station_repo):
        stations = [_make_station(), _make_station()]
        mock_station_repo.get_all_active_filtered.return_value = stations

        ctx = _make_access_ctx(role=UserRole.ADMIN)
        result = await station_service.get_all_active_stations_for_user(ctx)

        assert len(result) == 2
        mock_station_repo.get_all_active_filtered.assert_called_once_with(
            allowed_station_ids=None,
        )

    @pytest.mark.asyncio
    async def test_trader_filtered(self, station_service, mock_station_repo):
        sid = uuid4()
        stations = [_make_station(id=sid)]
        mock_station_repo.get_all_active_filtered.return_value = stations

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=[sid])
        result = await station_service.get_all_active_stations_for_user(ctx)

        assert len(result) == 1
        mock_station_repo.get_all_active_filtered.assert_called_once_with(
            allowed_station_ids=(sid,),
        )


class TestGetAllActiveDevicesForUser:
    @pytest.mark.asyncio
    async def test_admin_full_access(self, station_service, mock_storage_repo, mock_station_repo):
        station = _make_station()
        device = MagicMock()
        device.id = uuid4()
        device.station_id = station.id
        mock_storage_repo.get_all_active_filtered.return_value = [device]
        mock_station_repo.get_by_ids.return_value = [station]

        ctx = _make_access_ctx(role=UserRole.ADMIN)
        devices, name_map = await station_service.get_all_active_devices_for_user(ctx)

        assert len(devices) == 1
        mock_storage_repo.get_all_active_filtered.assert_called_once_with(
            allowed_device_ids=None,
            allowed_station_ids=None,
        )

    @pytest.mark.asyncio
    async def test_operator_filtered(self, station_service, mock_storage_repo, mock_station_repo):
        did = uuid4()
        sid = uuid4()
        station = _make_station(id=sid)
        device = MagicMock()
        device.id = did
        device.station_id = station.id
        mock_storage_repo.get_all_active_filtered.return_value = [device]
        mock_station_repo.get_by_ids.return_value = [station]

        ctx = _make_access_ctx(role=UserRole.STORAGE_OPERATOR, station_ids=[sid], device_ids=[did])
        devices, name_map = await station_service.get_all_active_devices_for_user(ctx)

        assert len(devices) == 1
        mock_storage_repo.get_all_active_filtered.assert_called_once_with(
            allowed_device_ids=(did,),
            allowed_station_ids=(sid,),
        )

    @pytest.mark.asyncio
    async def test_trader_filtered_by_station(self, station_service, mock_storage_repo, mock_station_repo):
        """trader 设备过滤基于 station_ids（绑定电站下的设备）"""
        sid = uuid4()
        station = _make_station(id=sid)
        device = MagicMock()
        device.id = uuid4()
        device.station_id = sid
        mock_storage_repo.get_all_active_filtered.return_value = [device]
        mock_station_repo.get_by_ids.return_value = [station]

        ctx = _make_access_ctx(role=UserRole.TRADER, station_ids=[sid])
        devices, name_map = await station_service.get_all_active_devices_for_user(ctx)

        assert len(devices) == 1
        mock_storage_repo.get_all_active_filtered.assert_called_once_with(
            allowed_device_ids=None,
            allowed_station_ids=(sid,),
        )

    @pytest.mark.asyncio
    async def test_empty_devices(self, station_service, mock_storage_repo):
        mock_storage_repo.get_all_active_filtered.return_value = []

        ctx = _make_access_ctx(role=UserRole.STORAGE_OPERATOR, station_ids=(), device_ids=())
        devices, name_map = await station_service.get_all_active_devices_for_user(ctx)

        assert devices == []
        assert name_map == {}
