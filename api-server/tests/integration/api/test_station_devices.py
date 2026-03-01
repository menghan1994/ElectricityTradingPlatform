"""电站储能设备子资源端点 API 路由测试。

注意：本文件通过 mock Service 层测试路由注册、权限拦截和序列化，
并非真正的 Service→Repository→DB 端到端集成测试。
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.station import PowerStation
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


def _make_station_obj(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid4(),
        "name": "测试电站",
        "province": "gansu",
        "capacity_mw": Decimal("50.00"),
        "station_type": "solar",
        "grid_connection_point": None,
        "has_storage": True,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    station = MagicMock(spec=PowerStation)
    for k, v in defaults.items():
        setattr(station, k, v)
    return station


def _make_device_obj(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid4(),
        "station_id": uuid4(),
        "name": "测试储能设备",
        "capacity_mwh": Decimal("100.00"),
        "max_charge_rate_mw": Decimal("50.00"),
        "max_discharge_rate_mw": Decimal("50.00"),
        "soc_upper_limit": Decimal("0.9000"),
        "soc_lower_limit": Decimal("0.1000"),
        "battery_type": "lfp",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    device = MagicMock(spec=StorageDevice)
    for k, v in defaults.items():
        setattr(device, k, v)
    return device


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestListStationDevices:
    @pytest.mark.asyncio
    async def test_list_devices_success(self, api_client):
        admin = _make_user_obj(role="admin")
        station = _make_station_obj()
        device = _make_device_obj(station_id=station.id)

        from app.core.data_access import DataAccessContext, get_data_access_context
        from app.core.dependencies import get_current_active_user

        mock_service = AsyncMock()
        mock_service.get_station_with_devices.return_value = (station, [device])

        from app.api.v1.stations import _get_station_service
        admin_ctx = DataAccessContext(
            user_id=admin.id, role="admin", station_ids=None, device_ids=None,
        )
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[get_data_access_context] = lambda: admin_ctx
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            f"/api/v1/stations/{station.id}/devices",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "测试储能设备"
        # M8: 验证响应体内容而非仅状态码
        assert data[0]["capacity_mwh"] == "100.00"
        assert data[0]["battery_type"] == "lfp"
        assert data[0]["is_active"] is True


class TestUpdateStationDevice:
    @pytest.mark.asyncio
    async def test_update_device_success(self, api_client):
        admin = _make_user_obj(role="admin")
        station = _make_station_obj()
        device = _make_device_obj(station_id=station.id)

        from app.api.v1.stations import _get_wizard_service
        from app.core.dependencies import get_current_active_user

        mock_wizard = AsyncMock()
        mock_wizard.update_storage_device.return_value = device

        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_wizard_service] = lambda: mock_wizard

        response = await api_client.put(
            f"/api/v1/stations/{station.id}/devices/{device.id}",
            json={"soc_upper_limit": "0.95"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        # M8: 验证响应体序列化正确
        data = response.json()
        assert data["name"] == "测试储能设备"
        assert data["soc_upper_limit"] == "0.9000"

    @pytest.mark.asyncio
    async def test_update_device_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}/devices/{uuid4()}",
            json={"name": "新名称"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestDeleteStationDevice:
    @pytest.mark.asyncio
    async def test_delete_device_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}/devices/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
