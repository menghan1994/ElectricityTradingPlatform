"""WizardService 单元测试 — Mock Repository 依赖，验证业务逻辑。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.schemas.storage import StorageDeviceAddInput
from app.schemas.wizard import StationWizardCreate, WizardStorageDeviceInput
from app.services.wizard_service import WizardService


@pytest.fixture
def mock_station_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_storage_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def wizard_service(mock_station_repo, mock_storage_repo, mock_audit_service):
    return WizardService(mock_station_repo, mock_storage_repo, mock_audit_service)


def _make_admin():
    admin = MagicMock()
    admin.id = uuid4()
    admin.username = "admin"
    admin.role = "admin"
    return admin


def _make_station_obj(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "测试电站",
        "province": "gansu",
        "capacity_mw": Decimal("50.00"),
        "station_type": "solar",
        "grid_connection_point": None,
        "has_storage": False,
        "is_active": True,
    }
    defaults.update(kwargs)
    station = MagicMock(spec=PowerStation)
    for k, v in defaults.items():
        setattr(station, k, v)
    return station


def _make_device_obj(**kwargs):
    defaults = {
        "id": uuid4(),
        "station_id": uuid4(),
        "name": "1号储能",
        "capacity_mwh": Decimal("100.00"),
        "max_charge_rate_mw": Decimal("50.00"),
        "max_discharge_rate_mw": Decimal("50.00"),
        "soc_upper_limit": Decimal("0.9"),
        "soc_lower_limit": Decimal("0.1"),
        "battery_type": "lfp",
        "is_active": True,
    }
    defaults.update(kwargs)
    device = MagicMock(spec=StorageDevice)
    for k, v in defaults.items():
        setattr(device, k, v)
    return device


class TestCreateStationWithDevices:
    @pytest.mark.asyncio
    async def test_create_station_no_storage(self, wizard_service, mock_station_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station_obj()
        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.return_value = station

        data = StationWizardCreate(
            name="甘肃某光伏电站",
            province="gansu",
            capacity_mw=50.00,
            station_type="solar",
            has_storage=False,
        )

        result_station, result_devices = await wizard_service.create_station_with_devices(admin, data, "127.0.0.1")

        assert result_station is station
        assert result_devices == []
        mock_station_repo.create.assert_called_once()
        # H5: 验证审计日志内容（不仅仅是 call_count）
        mock_audit_service.log_action.assert_called_once()
        audit_call = mock_audit_service.log_action.call_args
        assert audit_call.kwargs["action"] == "create_station"
        assert audit_call.kwargs["resource_type"] == "power_station"
        assert audit_call.kwargs["resource_id"] == station.id
        assert audit_call.kwargs["ip_address"] == "127.0.0.1"
        assert "name" in audit_call.kwargs["changes_after"]

    @pytest.mark.asyncio
    async def test_create_station_with_storage(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station_obj(has_storage=True)

        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.return_value = station
        # M1: add_all 是同步方法，使用 MagicMock 避免 RuntimeWarning
        mock_storage_repo.session.add_all = MagicMock()

        data = StationWizardCreate(
            name="甘肃某光伏电站",
            province="gansu",
            capacity_mw=50.00,
            station_type="solar",
            has_storage=True,
            storage_devices=[
                WizardStorageDeviceInput(
                    name="1号储能",
                    capacity_mwh=100,
                    max_charge_rate_mw=50,
                    max_discharge_rate_mw=50,
                    battery_type="lfp",
                ),
            ],
        )

        result_station, result_devices = await wizard_service.create_station_with_devices(admin, data, "127.0.0.1")

        assert result_station is station
        assert len(result_devices) == 1
        # M1: 现在使用 session.add_all + flush 批量创建
        mock_storage_repo.session.add_all.assert_called_once()
        mock_storage_repo.session.flush.assert_awaited_once()
        # H5: 审计日志内容验证 — 电站1条 + 设备1条 = 2条
        assert mock_audit_service.log_action.call_count == 2
        station_audit = mock_audit_service.log_action.call_args_list[0]
        assert station_audit.kwargs["action"] == "create_station"
        assert station_audit.kwargs["resource_type"] == "power_station"
        device_audit = mock_audit_service.log_action.call_args_list[1]
        assert device_audit.kwargs["action"] == "create_storage_device"
        assert device_audit.kwargs["resource_type"] == "storage_device"
        assert "battery_type" in device_audit.kwargs["changes_after"]

    @pytest.mark.asyncio
    async def test_create_station_with_multiple_devices(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """H7: 多设备批量创建测试 — 确保所有设备都被创建并审计。"""
        admin = _make_admin()
        station = _make_station_obj(has_storage=True)

        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.return_value = station
        mock_storage_repo.session.add_all = MagicMock()

        data = StationWizardCreate(
            name="甘肃某光伏电站",
            province="gansu",
            capacity_mw=50.00,
            station_type="solar",
            has_storage=True,
            storage_devices=[
                WizardStorageDeviceInput(
                    name="1号储能",
                    capacity_mwh=100,
                    max_charge_rate_mw=50,
                    max_discharge_rate_mw=50,
                    battery_type="lfp",
                ),
                WizardStorageDeviceInput(
                    name="2号储能",
                    capacity_mwh=200,
                    max_charge_rate_mw=80,
                    max_discharge_rate_mw=80,
                    battery_type="nmc",
                ),
            ],
        )

        result_station, result_devices = await wizard_service.create_station_with_devices(admin, data, "127.0.0.1")

        assert result_station is station
        assert len(result_devices) == 2
        mock_storage_repo.session.add_all.assert_called_once()
        # 验证 add_all 接收了 2 个设备
        added_devices = mock_storage_repo.session.add_all.call_args[0][0]
        assert len(added_devices) == 2
        # 审计日志：电站1条 + 设备2条 = 3条
        assert mock_audit_service.log_action.call_count == 3

    @pytest.mark.asyncio
    async def test_duplicate_name_raises(self, wizard_service, mock_station_repo):
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = _make_station_obj()

        data = StationWizardCreate(
            name="已存在电站",
            province="gansu",
            capacity_mw=50,
            station_type="solar",
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.create_station_with_devices(admin, data)

        assert exc_info.value.code == "STATION_NAME_DUPLICATE"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_soc_range_raises(self, wizard_service, mock_station_repo):
        """Service 层 SOC 校验（绕过 Pydantic 使用 model_construct）。"""
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = None

        # 使用 model_construct 绕过 Pydantic model_validator，直接测试 service 层校验
        bad_device = WizardStorageDeviceInput.model_construct(
            name="设备",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
            soc_upper_limit=Decimal("0.1"),
            soc_lower_limit=Decimal("0.9"),
            battery_type=None,
        )
        data = StationWizardCreate.model_construct(
            name="电站",
            province="gansu",
            capacity_mw=Decimal("50"),
            station_type="solar",
            grid_connection_point=None,
            has_storage=True,
            storage_devices=[bad_device],
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.create_station_with_devices(admin, data)

        assert exc_info.value.code == "INVALID_SOC_RANGE"
        assert exc_info.value.status_code == 422


class TestUpdateStorageDevice:
    @pytest.mark.asyncio
    async def test_update_device_soc_single_field(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """SOC 单字段更新时合并 DB 值做完整交叉校验。"""
        admin = _make_admin()
        station = _make_station_obj()
        device = _make_device_obj(
            station_id=station.id,
            soc_upper_limit=Decimal("0.9"),
            soc_lower_limit=Decimal("0.1"),
        )

        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = device
        mock_storage_repo.session = AsyncMock()

        # 仅更新上限为 0.95 — 应该与 DB 的 lower=0.1 做交叉校验，通过
        result = await wizard_service.update_storage_device(
            admin, station.id, device.id, {"soc_upper_limit": Decimal("0.95")},
        )
        assert result is device

    @pytest.mark.asyncio
    async def test_update_device_soc_single_field_invalid(self, wizard_service, mock_station_repo, mock_storage_repo):
        """SOC 单字段更新导致交叉校验失败。"""
        admin = _make_admin()
        station = _make_station_obj()
        device = _make_device_obj(
            station_id=station.id,
            soc_upper_limit=Decimal("0.9"),
            soc_lower_limit=Decimal("0.5"),
        )

        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = device

        # 尝试将上限改为 0.3 — 与 DB 的 lower=0.5 冲突
        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.update_storage_device(
                admin, station.id, device.id, {"soc_upper_limit": Decimal("0.3")},
            )
        assert exc_info.value.code == "INVALID_SOC_RANGE"

    @pytest.mark.asyncio
    async def test_update_device_not_found(self, wizard_service, mock_station_repo, mock_storage_repo):
        admin = _make_admin()
        station = _make_station_obj()
        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.update_storage_device(
                admin, station.id, uuid4(), {"name": "新名称"},
            )
        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_device_wrong_station(self, wizard_service, mock_station_repo, mock_storage_repo):
        admin = _make_admin()
        station = _make_station_obj()
        other_station_id = uuid4()
        device = _make_device_obj(station_id=other_station_id)

        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = device

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.update_storage_device(
                admin, station.id, device.id, {"name": "新名称"},
            )
        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_device_station_inactive(self, wizard_service, mock_station_repo, mock_storage_repo):
        """C2: update_storage_device 检查 station.is_active。"""
        admin = _make_admin()
        station = _make_station_obj(is_active=False)
        mock_station_repo.get_by_id.return_value = station

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.update_storage_device(
                admin, station.id, uuid4(), {"name": "新名称"},
            )
        assert exc_info.value.code == "STATION_INACTIVE"

    @pytest.mark.asyncio
    async def test_update_device_inactive(self, wizard_service, mock_station_repo, mock_storage_repo):
        """C2: update_storage_device 检查 device.is_active。"""
        admin = _make_admin()
        station = _make_station_obj()
        device = _make_device_obj(station_id=station.id, is_active=False)

        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = device

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.update_storage_device(
                admin, station.id, device.id, {"name": "新名称"},
            )
        assert exc_info.value.code == "DEVICE_INACTIVE"

    @pytest.mark.asyncio
    async def test_update_device_rejects_forbidden_fields(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """H8+C4: 字段白名单对抗性测试 — is_active、station_id、id 等被拒绝。"""
        admin = _make_admin()
        station = _make_station_obj()
        device = _make_device_obj(station_id=station.id)

        mock_station_repo.get_by_id.return_value = station
        mock_storage_repo.get_by_id.return_value = device
        mock_storage_repo.session = AsyncMock()

        # 尝试注入 is_active、station_id、id 字段 — 全部应被白名单过滤
        result = await wizard_service.update_storage_device(
            admin, station.id, device.id,
            {"is_active": False, "station_id": uuid4(), "id": uuid4()},
        )

        # 设备字段不应被更改
        assert device.is_active is True
        # 无实际变更 → 无审计日志
        mock_audit_service.log_action.assert_not_called()


class TestIntegrityErrorRaceConditions:
    """C4: IntegrityError 竞态条件路径测试。"""

    @pytest.mark.asyncio
    async def test_station_create_integrity_error(self, wizard_service, mock_station_repo):
        """并发创建同名电站时 IntegrityError 转为 STATION_NAME_DUPLICATE。"""
        admin = _make_admin()
        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.side_effect = IntegrityError("", {}, Exception())

        data = StationWizardCreate(
            name="并发电站",
            province="gansu",
            capacity_mw=50,
            station_type="solar",
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.create_station_with_devices(admin, data)
        assert exc_info.value.code == "STATION_NAME_DUPLICATE"
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_device_batch_create_integrity_error(self, wizard_service, mock_station_repo, mock_storage_repo):
        """批量创建设备时 IntegrityError 转为 DEVICE_NAME_DUPLICATE。"""
        admin = _make_admin()
        station = _make_station_obj(has_storage=True)
        mock_station_repo.get_by_name.return_value = None
        mock_station_repo.create.return_value = station
        mock_storage_repo.session.add_all = MagicMock()
        mock_storage_repo.session.flush.side_effect = IntegrityError("", {}, Exception())

        data = StationWizardCreate(
            name="电站",
            province="gansu",
            capacity_mw=50,
            station_type="solar",
            has_storage=True,
            storage_devices=[
                WizardStorageDeviceInput(
                    name="重复设备",
                    capacity_mwh=100,
                    max_charge_rate_mw=50,
                    max_discharge_rate_mw=50,
                ),
            ],
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.create_station_with_devices(admin, data)
        assert exc_info.value.code == "DEVICE_NAME_DUPLICATE"
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_add_device_integrity_error(self, wizard_service, mock_station_repo, mock_storage_repo):
        """add_device_to_station IntegrityError 转为 DEVICE_NAME_DUPLICATE。"""
        admin = _make_admin()
        station = _make_station_obj()
        # H1: 使用 FOR UPDATE mock 模式
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = station
        mock_station_repo.session.execute.return_value = mock_result
        mock_storage_repo.get_by_station_id.return_value = []  # M4: 设备数量检查
        mock_storage_repo.create.side_effect = IntegrityError("", {}, Exception())

        data = StorageDeviceAddInput(
            name="重复设备",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.add_device_to_station(admin, station.id, data)
        assert exc_info.value.code == "DEVICE_NAME_DUPLICATE"


class TestAddDeviceToStation:
    """H4: add_device_to_station 单元测试。"""

    def _mock_session_execute(self, mock_station_repo, station):
        """H1: Mock session.execute for FOR UPDATE query."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = station
        mock_station_repo.session.execute.return_value = mock_result

    @pytest.mark.asyncio
    async def test_add_device_success(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station_obj(has_storage=False)
        created_device = _make_device_obj(station_id=station.id)

        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_station_id.return_value = []  # M4: 设备数量检查
        mock_storage_repo.create.return_value = created_device

        data = StorageDeviceAddInput(
            name="1号储能",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
        )

        result = await wizard_service.add_device_to_station(admin, station.id, data, "127.0.0.1")
        assert result is created_device
        mock_storage_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_device_station_not_found(self, wizard_service, mock_station_repo):
        admin = _make_admin()
        self._mock_session_execute(mock_station_repo, None)

        data = StorageDeviceAddInput(
            name="设备",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.add_device_to_station(admin, uuid4(), data)
        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_device_station_inactive(self, wizard_service, mock_station_repo):
        admin = _make_admin()
        station = _make_station_obj(is_active=False)
        self._mock_session_execute(mock_station_repo, station)

        data = StorageDeviceAddInput(
            name="设备",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.add_device_to_station(admin, station.id, data)
        assert exc_info.value.code == "STATION_INACTIVE"

    @pytest.mark.asyncio
    async def test_add_device_syncs_has_storage(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """H5: 添加设备到 has_storage=false 的电站时同步标志。"""
        admin = _make_admin()
        station = _make_station_obj(has_storage=False)
        created_device = _make_device_obj(station_id=station.id)

        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_station_id.return_value = []  # M4: 设备数量检查
        mock_storage_repo.create.return_value = created_device

        data = StorageDeviceAddInput(
            name="1号储能",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
        )

        await wizard_service.add_device_to_station(admin, station.id, data)
        assert station.has_storage is True

    @pytest.mark.asyncio
    async def test_add_device_soc_invalid(self, wizard_service, mock_station_repo, mock_storage_repo):
        admin = _make_admin()
        station = _make_station_obj()
        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_station_id.return_value = []  # M4: 设备数量检查

        data = StorageDeviceAddInput.model_construct(
            name="设备",
            capacity_mwh=Decimal("100"),
            max_charge_rate_mw=Decimal("50"),
            max_discharge_rate_mw=Decimal("50"),
            soc_upper_limit=Decimal("0.1"),
            soc_lower_limit=Decimal("0.9"),
            battery_type=None,
        )

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.add_device_to_station(admin, station.id, data)
        assert exc_info.value.code == "INVALID_SOC_RANGE"


class TestDeleteStationDevice:
    """H4: delete_station_device 单元测试。"""

    def _mock_session_execute(self, mock_station_repo, station):
        """Mock session.execute for FOR UPDATE query."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = station
        mock_station_repo.session.execute.return_value = mock_result

    @pytest.mark.asyncio
    async def test_delete_device_success(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        admin = _make_admin()
        station = _make_station_obj(has_storage=True)
        device = _make_device_obj(station_id=station.id)
        other_device = _make_device_obj(station_id=station.id, name="2号储能")

        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_id.return_value = device
        mock_storage_repo.get_by_station_id.return_value = [other_device]

        await wizard_service.delete_station_device(admin, station.id, device.id, "127.0.0.1")

        assert device.is_active is False
        assert station.has_storage is True  # 还有其他设备
        mock_audit_service.log_action.assert_called()

    @pytest.mark.asyncio
    async def test_delete_last_device_syncs_has_storage(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """H5: 删除最后一个设备时 has_storage 同步为 False。"""
        admin = _make_admin()
        station = _make_station_obj(has_storage=True)
        device = _make_device_obj(station_id=station.id)

        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_id.return_value = device
        mock_storage_repo.get_by_station_id.return_value = []  # 无剩余设备

        await wizard_service.delete_station_device(admin, station.id, device.id)

        assert device.is_active is False
        assert station.has_storage is False

    @pytest.mark.asyncio
    async def test_delete_device_station_not_found(self, wizard_service, mock_station_repo):
        admin = _make_admin()
        self._mock_session_execute(mock_station_repo, None)

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.delete_station_device(admin, uuid4(), uuid4())
        assert exc_info.value.code == "STATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_device_station_inactive(self, wizard_service, mock_station_repo):
        admin = _make_admin()
        station = _make_station_obj(is_active=False)
        self._mock_session_execute(mock_station_repo, station)

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.delete_station_device(admin, station.id, uuid4())
        assert exc_info.value.code == "STATION_INACTIVE"

    @pytest.mark.asyncio
    async def test_delete_device_not_found(self, wizard_service, mock_station_repo, mock_storage_repo):
        admin = _make_admin()
        station = _make_station_obj()
        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_id.return_value = None

        with pytest.raises(BusinessError) as exc_info:
            await wizard_service.delete_station_device(admin, station.id, uuid4())
        assert exc_info.value.code == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_device_already_inactive(self, wizard_service, mock_station_repo, mock_storage_repo, mock_audit_service):
        """已停用设备不重复删除（no-op）。"""
        admin = _make_admin()
        station = _make_station_obj()
        device = _make_device_obj(station_id=station.id, is_active=False)

        self._mock_session_execute(mock_station_repo, station)
        mock_storage_repo.get_by_id.return_value = device

        await wizard_service.delete_station_device(admin, station.id, device.id)
        mock_audit_service.log_action.assert_not_called()
