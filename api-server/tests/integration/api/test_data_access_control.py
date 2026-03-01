"""数据访问控制集成测试 — 验证各角色的数据访问权限。

覆盖场景：
- trader 只能看到绑定电站
- storage_operator 只能看到绑定设备
- trading_manager 看到所有电站
- executive_readonly 可读不可写（403）
- 未认证用户 401
- admin 全权限
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.data_access import DataAccessContext
from app.main import app
from app.models.station import PowerStation
from app.models.user import User, UserRole
from app.schemas.user import RoleType


def _make_user_obj(role: RoleType = UserRole.ADMIN) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = f"test_{role}"
    user.role = role
    user.is_active = True
    user.is_locked = False
    return user


def _make_station_obj(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid4(),
        "name": "测试电站",
        "province": "guangdong",
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


def _make_data_access_context(role, station_ids=None, device_ids=None):
    return DataAccessContext(
        user_id=uuid4(), role=role,
        station_ids=tuple(station_ids) if station_ids is not None else None,
        device_ids=tuple(device_ids) if device_ids is not None else None,
    )


def _create_mock_station_service(stations=None):
    from app.services.station_service import StationService

    service = AsyncMock(spec=StationService)
    if stations is None:
        stations = [_make_station_obj(name=f"电站{i}") for i in range(3)]

    service.list_stations_for_user.return_value = (stations, len(stations))
    service.get_station_for_user.return_value = stations[0] if stations else _make_station_obj()
    service.get_all_active_stations_for_user.return_value = stations
    service.get_all_active_devices_for_user.return_value = ([], {})
    service.create_station.return_value = stations[0] if stations else _make_station_obj()
    service.update_station.return_value = stations[0] if stations else None
    service.delete_station.return_value = None

    return service


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _setup_overrides(role, stations=None, station_ids=None, device_ids=None):
    """统一设置 dependency overrides"""
    from app.api.v1.stations import _get_station_service
    from app.core.data_access import get_data_access_context
    from app.core.dependencies import get_current_active_user

    user = _make_user_obj(role=role)
    ctx = _make_data_access_context(role, station_ids=station_ids, device_ids=device_ids)
    mock_service = _create_mock_station_service(stations)

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_data_access_context] = lambda: ctx
    app.dependency_overrides[_get_station_service] = lambda: mock_service

    return user, ctx, mock_service


class TestTraderDataAccess:
    """AC #1: 交易员仅能看到绑定电站的数据"""

    @pytest.mark.asyncio
    async def test_trader_can_list_stations(self, api_client):
        bound_station = _make_station_obj(name="绑定电站")
        _setup_overrides(
            UserRole.TRADER,
            stations=[bound_station],
            station_ids=[bound_station.id],
        )

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_trader_can_get_bound_station(self, api_client):
        bound_station = _make_station_obj(name="绑定电站")
        _setup_overrides(
            UserRole.TRADER,
            stations=[bound_station],
            station_ids=[bound_station.id],
        )

        response = await api_client.get(
            f"/api/v1/stations/{bound_station.id}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trader_cannot_create_station(self, api_client):
        """写操作保持 admin-only"""
        user = _make_user_obj(role=UserRole.TRADER)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "shandong",
                "capacity_mw": 50.00,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestStorageOperatorDataAccess:
    """AC #2: 储能运维员仅能看到绑定设备的数据"""

    @pytest.mark.asyncio
    async def test_operator_can_list_active_devices(self, api_client):
        did = uuid4()
        sid = uuid4()
        _setup_overrides(
            UserRole.STORAGE_OPERATOR,
            station_ids=[sid],
            device_ids=[did],
        )

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_can_list_stations(self, api_client):
        """storage_operator 应能列出绑定设备所属的电站"""
        sid = uuid4()
        bound_station = _make_station_obj(id=sid, name="设备所属电站")
        _setup_overrides(
            UserRole.STORAGE_OPERATOR,
            stations=[bound_station],
            station_ids=[sid],
            device_ids=[uuid4()],
        )

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestTraderDeviceAccess:
    """trader 只能看到绑定电站下的设备，不能无限制访问所有设备"""

    @pytest.mark.asyncio
    async def test_trader_devices_filtered_by_station(self, api_client):
        """trader 调用设备列表时，service 应使用 station_ids 过滤"""
        sid = uuid4()
        _, _, mock_service = _setup_overrides(
            UserRole.TRADER,
            station_ids=[sid],
        )

        response = await api_client.get(
            "/api/v1/stations/devices/active",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        mock_service.get_all_active_devices_for_user.assert_called_once()


class TestTradingManagerDataAccess:
    """AC #3: 交易主管可查看所有电站数据"""

    @pytest.mark.asyncio
    async def test_manager_sees_all_stations(self, api_client):
        stations = [_make_station_obj(name=f"电站{i}") for i in range(5)]
        _setup_overrides(UserRole.TRADING_MANAGER, stations=stations)

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5


class TestTradingManagerWriteAccess:
    """trading_manager 无电站写操作权限（写操作保持 admin-only）"""

    @pytest.mark.asyncio
    async def test_manager_cannot_create_station(self, api_client):
        user = _make_user_obj(role=UserRole.TRADING_MANAGER)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "shandong",
                "capacity_mw": 50.00,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_manager_cannot_update_station(self, api_client):
        user = _make_user_obj(role=UserRole.TRADING_MANAGER)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}",
            json={"province": "shandong"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_manager_cannot_delete_station(self, api_client):
        user = _make_user_obj(role=UserRole.TRADING_MANAGER)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestStorageOperatorWriteAccess:
    """storage_operator 无电站写操作权限（写操作保持 admin-only）"""

    @pytest.mark.asyncio
    async def test_operator_cannot_create_station(self, api_client):
        user = _make_user_obj(role=UserRole.STORAGE_OPERATOR)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "shandong",
                "capacity_mw": 50.00,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_operator_cannot_update_station(self, api_client):
        user = _make_user_obj(role=UserRole.STORAGE_OPERATOR)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}",
            json={"province": "shandong"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_operator_cannot_delete_station(self, api_client):
        user = _make_user_obj(role=UserRole.STORAGE_OPERATOR)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"


class TestExecutiveReadonlyDataAccess:
    """AC #4: 高管只读角色可读不可写"""

    @pytest.mark.asyncio
    async def test_readonly_can_list_stations(self, api_client):
        _setup_overrides(UserRole.EXECUTIVE_READONLY)

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_readonly_cannot_create_station(self, api_client):
        user = _make_user_obj(role=UserRole.EXECUTIVE_READONLY)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "shandong",
                "capacity_mw": 50.00,
                "station_type": "solar",
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_readonly_cannot_update_station(self, api_client):
        user = _make_user_obj(role=UserRole.EXECUTIVE_READONLY)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.put(
            f"/api/v1/stations/{uuid4()}",
            json={"province": "shandong"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_readonly_cannot_delete_station(self, api_client):
        user = _make_user_obj(role=UserRole.EXECUTIVE_READONLY)

        from app.core.dependencies import get_current_active_user
        app.dependency_overrides[get_current_active_user] = lambda: user

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 403


class TestUnauthenticatedAccess:
    """AC #5: 未认证用户返回 401"""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, api_client):
        # 不设置任何 overrides，不携带 Authorization header
        app.dependency_overrides.clear()

        response = await api_client.get("/api/v1/stations")

        assert response.status_code == 401


class TestRequireWritePermissionWiring:
    """验证 require_write_permission 依赖确实挂载在所有写端点上。

    背景：写端点同时声明 require_roles(["admin"]) 和 require_write_permission，
    但 require_roles 先行拦截非 admin 用户，导致 require_write_permission 在常规
    集成测试中从未被触发。此结构性测试通过反射确认依赖确实挂载，防止误删。
    """

    def test_all_write_endpoints_include_write_permission(self):
        import inspect

        from fastapi.params import Depends as DependsClass

        from app.api.v1.stations import create_station, delete_station, update_station
        from app.core.data_access import require_write_permission

        for endpoint in [create_station, update_station, delete_station]:
            sig = inspect.signature(endpoint)
            dep_funcs = [
                param.default.dependency
                for param in sig.parameters.values()
                if isinstance(param.default, DependsClass)
            ]
            assert require_write_permission in dep_funcs, (
                f"{endpoint.__name__} 缺少 require_write_permission 依赖"
            )


class TestAdminFullAccess:
    """Admin 全权限"""

    @pytest.mark.asyncio
    async def test_admin_can_list_all(self, api_client):
        stations = [_make_station_obj(name=f"电站{i}") for i in range(10)]
        _setup_overrides(UserRole.ADMIN, stations=stations)

        response = await api_client.get(
            "/api/v1/stations",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 10

    @pytest.mark.asyncio
    async def test_admin_can_create(self, api_client):
        _setup_overrides(UserRole.ADMIN)

        response = await api_client.post(
            "/api/v1/stations",
            json={
                "name": "新电站",
                "province": "shandong",
                "capacity_mw": 50.00,
                "station_type": "solar",
                "has_storage": False,
            },
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_admin_can_delete(self, api_client):
        _setup_overrides(UserRole.ADMIN)

        response = await api_client.delete(
            f"/api/v1/stations/{uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 204
