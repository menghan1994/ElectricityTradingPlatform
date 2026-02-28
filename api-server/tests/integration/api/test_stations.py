"""电站管理 API 集成测试 — 使用 dependency_overrides Mock 依赖，
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
from app.schemas.user import RoleType


def _make_user_obj(role: "RoleType" = "admin") -> MagicMock:
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


def _create_mock_station_service(stations=None):
    from app.services.station_service import StationService

    service = AsyncMock(spec=StationService)

    if stations is None:
        stations = [_make_station_obj(name=f"电站{i}") for i in range(3)]

    service.list_stations.return_value = (stations, len(stations))
    service.list_stations_for_user.return_value = (stations, len(stations))
    service.get_station.return_value = stations[0] if stations else None
    service.get_station_for_user.return_value = stations[0] if stations else _make_station_obj()
    service.create_station.return_value = stations[0] if stations else _make_station_obj()
    service.update_station.return_value = stations[0] if stations else None
    service.delete_station.return_value = None
    service.get_all_active_stations.return_value = stations
    service.get_all_active_stations_for_user.return_value = stations
    service.get_all_active_devices_for_user.return_value = ([], {})

    return service


def _make_data_access_context(user_id=None, role="admin", station_ids=None, device_ids=None):
    from app.core.data_access import DataAccessContext

    return DataAccessContext(
        user_id=user_id or uuid4(),
        role=role,
        station_ids=tuple(station_ids) if station_ids is not None else None,
        device_ids=tuple(device_ids) if device_ids is not None else None,
    )


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestListStationsEndpoint:
    @pytest.mark.asyncio
    async def test_list_stations_as_admin(self, api_client):
        mock_service = _create_mock_station_service()
        admin_ctx = _make_data_access_context(role="admin")

        from app.api.v1.stations import _get_station_service
        from app.core.data_access import get_data_access_context
        app.dependency_overrides[get_data_access_context] = lambda: admin_ctx
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_stations_accessible_for_trader(self, api_client):
        """Story 1.5: 交易员可以访问电站列表（数据由后端过滤）"""
        mock_service = _create_mock_station_service()
        trader_ctx = _make_data_access_context(role="trader", station_ids=[uuid4()])

        from app.api.v1.stations import _get_station_service
        from app.core.data_access import get_data_access_context
        app.dependency_overrides[get_data_access_context] = lambda: trader_ctx
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200


class TestCreateStationEndpoint:
    @pytest.mark.asyncio
    async def test_create_station_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "山东",
                "capacity_mw": 50.00,
                "station_type": "solar",
                "has_storage": False,
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "name" in data

    @pytest.mark.asyncio
    async def test_create_station_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "山东",
                "capacity_mw": 50.00,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestUpdateStationEndpoint:
    @pytest.mark.asyncio
    async def test_update_station_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}",
            json={"province": "山东"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_station_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}",
            json={"province": "山东"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestDeleteStationEndpoint:
    @pytest.mark.asyncio
    async def test_delete_station_as_admin(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_station_forbidden_for_trader(self, api_client):
        trader = _make_user_obj(role="trader")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: trader

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestErrorPaths:
    @pytest.mark.asyncio
    async def test_station_access_denied(self, api_client):
        """电站存在但用户无权访问时返回 403"""
        admin_ctx = _make_data_access_context(role="admin")
        mock_service = _create_mock_station_service()
        mock_service.get_station_for_user.side_effect = BusinessError(
            code="STATION_ACCESS_DENIED", message="无权访问该电站", status_code=403,
        )

        from app.api.v1.stations import _get_station_service
        from app.core.data_access import get_data_access_context
        app.dependency_overrides[get_data_access_context] = lambda: admin_ctx
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.get(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "STATION_ACCESS_DENIED"

    @pytest.mark.asyncio
    async def test_duplicate_station_name(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()
        mock_service.create_station.side_effect = BusinessError(
            code="STATION_NAME_EXISTS", message="电站名称已存在", status_code=409,
        )

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "重复电站",
                "province": "广东",
                "capacity_mw": 100.00,
                "station_type": "wind",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "STATION_NAME_EXISTS"

    @pytest.mark.asyncio
    async def test_invalid_payload(self, api_client):
        admin = _make_user_obj(role="admin")

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin

        response = await api_client.post(
            "/api/v1/stations",
            json={"name": ""},  # Missing required fields
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_station_not_found(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()
        mock_service.delete_station.side_effect = BusinessError(
            code="STATION_NOT_FOUND", message="电站不存在", status_code=404,
        )

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_station_has_bindings(self, api_client):
        admin = _make_user_obj(role="admin")
        mock_service = _create_mock_station_service()
        mock_service.delete_station.side_effect = BusinessError(
            code="STATION_HAS_BINDINGS", message="电站有活跃绑定关系，无法停用", status_code=409,
        )

        from app.api.v1.stations import _get_station_service
        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: admin
        app.dependency_overrides[_get_station_service] = lambda: mock_service

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "STATION_HAS_BINDINGS"
