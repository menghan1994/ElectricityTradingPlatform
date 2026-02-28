"""StationService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError
from app.models.station import PowerStation
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
        "province": "广东",
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
            province="山东",
            capacity_mw=Decimal("50.00"),
            station_type="solar",
            has_storage=False,
        )
        result = await station_service.create_station(admin, data, "192.168.1.1")

        assert result.name == "新电站"
        assert result.province == "山东"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_station_duplicate_name(self, station_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = _make_station()

        data = StationCreate(
            name="测试电站",
            province="广东",
            capacity_mw=Decimal("100.00"),
            station_type="wind",
        )

        with pytest.raises(BusinessError) as exc_info:
            await station_service.create_station(admin, data)

        assert exc_info.value.code == "STATION_NAME_EXISTS"
        assert exc_info.value.status_code == 409


class TestUpdateStation:
    @pytest.mark.asyncio
    async def test_update_station_success(self, station_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station()
        mock_station_repo.get_by_id.return_value = station

        data = StationUpdate(province="山东")
        result = await station_service.update_station(admin, station.id, data, "192.168.1.1")

        assert station.province == "山东"
        mock_audit_service.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_station_not_found(self, station_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_id.return_value = None

        data = StationUpdate(province="山东")

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

        assert exc_info.value.code == "STATION_NAME_EXISTS"


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
