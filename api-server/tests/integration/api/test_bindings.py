"""绑定管理 API 集成测试 — 使用 dependency_overrides Mock 依赖，
验证 API 层路由/权限守卫/响应格式。"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import BusinessError
from app.main import app
from app.models.station import PowerStation
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
        "province": "广东",
        "capacity_mw": Decimal("100.00"),
        "station_type": "wind",
        "grid_connection_point": None,
        "has_storage": False,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    station = MagicMock(spec=PowerStation)
    for k, v in defaults.items():
        setattr(station, k, v)
    return station


def _create_mock_binding_service():
    from app.services.binding_service import BindingService

    service = AsyncMock(spec=BindingService)

    stations = [_make_station_obj(name=f"电站{i}") for i in range(2)]
    station_ids = [s.id for s in stations]

    service.get_user_station_bindings.return_value = (station_ids, stations)
    service.update_user_station_bindings.return_value = (station_ids, stations)
    service.get_user_device_bindings.return_value = ([], [])
    service.update_user_device_bindings.return_value = ([], [])

    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestGetStationBindingsEndpoint:
    @pytest.mark.asyncio
    async def test_get_bindings_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        user_id = uuid4()
        response = await api_client.get(
            f"/api/v1/bindings/{user_id}/station_bindings",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "station_ids" in data
        assert "stations" in data

    @pytest.mark.asyncio
    async def test_get_bindings_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.get(
            f"/api/v1/bindings/{uuid4()}/station_bindings",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestUpdateStationBindingsEndpoint:
    @pytest.mark.asyncio
    async def test_update_bindings_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        user_id = uuid4()
        station_ids = [str(uuid4()), str(uuid4())]
        response = await api_client.put(
            f"/api/v1/bindings/{user_id}/station_bindings",
            json={"station_ids": station_ids},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "station_ids" in data
        assert "stations" in data

    @pytest.mark.asyncio
    async def test_update_bindings_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/station_bindings",
            json={"station_ids": []},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestDeviceBindingsEndpoint:
    @pytest.mark.asyncio
    async def test_get_device_bindings_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.get(
            f"/api/v1/bindings/{uuid4()}/device_bindings",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "device_ids" in data
        assert "devices" in data

    @pytest.mark.asyncio
    async def test_update_device_bindings_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/device_bindings",
            json={"device_ids": []},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "device_ids" in data
        assert "devices" in data

    @pytest.mark.asyncio
    async def test_get_device_bindings_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.get(
            f"/api/v1/bindings/{uuid4()}/device_bindings",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_device_bindings_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/device_bindings",
            json={"device_ids": []},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestInvalidInput:
    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, api_client):
        admin = _make_user_obj(role="admin")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin

        response = await api_client.get(
            "/api/v1/bindings/not-a-uuid/station_bindings",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422


class TestBindingErrorPaths:
    @pytest.mark.asyncio
    async def test_role_binding_mismatch(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()
        mock_service.update_user_station_bindings.side_effect = BusinessError(
            code="ROLE_BINDING_MISMATCH",
            message="仅交易员(trader)可绑定电站",
            status_code=422,
        )

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/station_bindings",
            json={"station_ids": [str(uuid4())]},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "ROLE_BINDING_MISMATCH"

    @pytest.mark.asyncio
    async def test_station_not_found(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()
        mock_service.update_user_station_bindings.side_effect = BusinessError(
            code="STATION_NOT_FOUND",
            message="部分电站不存在",
            status_code=404,
        )

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/station_bindings",
            json={"station_ids": [str(uuid4())]},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_user_not_found(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()
        mock_service.update_user_station_bindings.side_effect = BusinessError(
            code="USER_NOT_FOUND",
            message="用户不存在",
            status_code=404,
        )

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/station_bindings",
            json={"station_ids": []},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_device_binding_role_mismatch(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_binding_service()
        mock_service.update_user_device_bindings.side_effect = BusinessError(
            code="ROLE_BINDING_MISMATCH",
            message="仅储能运维员(storage_operator)可绑定设备",
            status_code=422,
        )

        from app.api.v1.bindings import _get_binding_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_binding_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/bindings/{uuid4()}/device_bindings",
            json={"device_ids": [str(uuid4())]},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "ROLE_BINDING_MISMATCH"
