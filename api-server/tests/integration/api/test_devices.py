"""储能设备 API 集成测试 — 使用 dependency_overrides Mock 依赖。"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.storage import StorageDevice
from app.models.user import User


def _make_user_obj(role: str = "admin") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "admin"
    user.role = role
    user.is_active = True
    user.is_locked = False
    return user


def _make_device_obj(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid4(),
        "station_id": uuid4(),
        "name": "测试储能设备",
        "capacity_mwh": Decimal("50.00"),
        "max_charge_rate_mw": Decimal("10.00"),
        "max_discharge_rate_mw": Decimal("10.00"),
        "soc_upper_limit": Decimal("0.9"),
        "soc_lower_limit": Decimal("0.1"),
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    device = MagicMock(spec=StorageDevice)
    for k, v in defaults.items():
        setattr(device, k, v)
    return device


def _create_mock_station_service(devices=None):
    from app.services.station_service import StationService

    service = AsyncMock(spec=StationService)
    if devices is None:
        devices = [_make_device_obj(name=f"设备{i}") for i in range(3)]
    service.get_all_active_devices.return_value = devices
    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestListActiveDevicesEndpoint:
    @pytest.mark.asyncio
    async def test_list_active_devices_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        station_id = uuid4()
        devices = [_make_device_obj(name=f"设备{i}", station_id=station_id) for i in range(3)]
        mock_service = AsyncMock()
        station_name_map = {str(station_id): "测试电站"}
        mock_service.get_all_active_devices_with_station_names.return_value = (devices, station_name_map)

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["name"] == "设备0"
        # 验证所有字段存在且类型正确
        for item in data:
            assert "id" in item
            assert "station_id" in item
            assert "name" in item
            assert "capacity_mwh" in item
            assert "is_active" in item
            assert item["is_active"] is True
        # 验证 station_name 已正确填充
        assert data[0]["station_name"] == "测试电站"

    @pytest.mark.asyncio
    async def test_list_active_devices_empty_list(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = AsyncMock()
        mock_service.get_all_active_devices_with_station_names.return_value = ([], {})

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_active_devices_without_station_name(self, api_client):
        """station_name_map 中无对应电站时，station_name 应为 null"""
        admin = _make_user_obj(role="admin")
        devices = [_make_device_obj(name="孤立设备")]
        mock_service = AsyncMock()
        mock_service.get_all_active_devices_with_station_names.return_value = (devices, {})

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["station_name"] is None

    @pytest.mark.asyncio
    async def test_list_active_devices_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
