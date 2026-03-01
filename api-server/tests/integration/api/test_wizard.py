"""向导 API 端点测试。

注意：这些测试使用 dependency_overrides mock Service 层，验证的是 API 路由层
（HTTP 请求解析、Pydantic schema 校验、权限校验、响应序列化）。
Service→Repository→DB 层的集成测试覆盖在 unit/services/ 和 unit/repositories/ 中。
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
        "name": "甘肃某光伏电站",
        "province": "gansu",
        "capacity_mw": Decimal("50.00"),
        "station_type": "solar",
        "grid_connection_point": "330kV 某某变电站",
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
        "name": "1号储能系统",
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


def _create_mock_wizard_service():
    from app.services.wizard_service import WizardService

    service = AsyncMock(spec=WizardService)
    station = _make_station_obj()
    device = _make_device_obj(station_id=station.id)
    service.create_station_with_devices.return_value = (station, [device])
    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestWizardCreateStation:
    @pytest.mark.asyncio
    async def test_admin_creates_station_with_storage(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_wizard_service()

        from app.api.v1.wizard import _get_wizard_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_wizard_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "甘肃某光伏电站",
                "province": "gansu",
                "capacity_mw": 50.00,
                "station_type": "solar",
                "grid_connection_point": "330kV 某某变电站",
                "has_storage": True,
                "storage_devices": [
                    {
                        "name": "1号储能系统",
                        "capacity_mwh": 100.00,
                        "max_charge_rate_mw": 50.00,
                        "max_discharge_rate_mw": 50.00,
                        "soc_upper_limit": 0.9,
                        "soc_lower_limit": 0.1,
                        "battery_type": "lfp",
                    },
                ],
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "station" in data
        assert "devices" in data
        assert len(data["devices"]) == 1

    @pytest.mark.asyncio
    async def test_admin_creates_station_no_storage(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_wizard_service()

        station = _make_station_obj(has_storage=False)
        mock_service.create_station_with_devices.return_value = (station, [])

        from app.api.v1.wizard import _get_wizard_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_wizard_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "纯发电电站",
                "province": "gansu",
                "capacity_mw": 50.00,
                "station_type": "wind",
                "has_storage": False,
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["devices"]) == 0

    @pytest.mark.asyncio
    async def test_soc_out_of_range_returns_422(self, api_client):
        admin = _make_user_obj(role="admin")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "电站",
                "province": "gansu",
                "capacity_mw": 50,
                "station_type": "solar",
                "has_storage": True,
                "storage_devices": [
                    {
                        "name": "设备",
                        "capacity_mwh": 100,
                        "max_charge_rate_mw": 50,
                        "max_discharge_rate_mw": 50,
                        "soc_upper_limit": 0.1,
                        "soc_lower_limit": 0.9,
                    },
                ],
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_non_admin_returns_403(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "电站",
                "province": "gansu",
                "capacity_mw": 50,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_duplicate_name_returns_409(self, api_client):
        from app.core.exceptions import BusinessError

        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_wizard_service()
        mock_service.create_station_with_devices.side_effect = BusinessError(
            code="STATION_NAME_DUPLICATE",
            message="电站名称已存在",
            status_code=409,
        )

        from app.api.v1.wizard import _get_wizard_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_wizard_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "已存在",
                "province": "gansu",
                "capacity_mw": 50,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "STATION_NAME_DUPLICATE"

    @pytest.mark.asyncio
    async def test_invalid_province_returns_422(self, api_client):
        """H6: 服务端省份校验 — 无效省份名返回 422。"""
        admin = _make_user_obj(role="admin")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin

        response = await api_client.post(
            "/api/v1/wizard/stations",
            json={
                "name": "电站",
                "province": "invalid_province",
                "capacity_mw": 50,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422
