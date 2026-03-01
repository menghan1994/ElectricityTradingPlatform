from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.models.user import User
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.schemas.storage import StorageDeviceAddInput
from app.schemas.wizard import StationWizardCreate
from app.services.audit_service import AuditService

logger = structlog.get_logger()

# H2+C4: 允许通过 setattr 更新的字段白名单
# is_active 不在此列表中 — 设备停用必须通过 delete_station_device，
# 以确保 FOR UPDATE 锁、has_storage 同步和正确审计
_DEVICE_UPDATE_FIELDS = frozenset({
    "name", "capacity_mwh", "max_charge_rate_mw", "max_discharge_rate_mw",
    "soc_upper_limit", "soc_lower_limit", "battery_type",
})


class WizardService:
    def __init__(
        self,
        station_repo: StationRepository,
        storage_repo: StorageDeviceRepository,
        audit_service: AuditService,
    ):
        self.station_repo = station_repo
        self.storage_repo = storage_repo
        self.audit_service = audit_service

    def _validate_soc_range(self, lower: Decimal, upper: Decimal, device_name: str) -> None:
        if lower < 0 or upper > 1 or lower >= upper:
            raise BusinessError(
                code="INVALID_SOC_RANGE",
                message=f"储能设备 '{device_name}' 的 SOC 范围无效：下限 {lower}，上限 {upper}",
                status_code=422,
            )

    async def create_station_with_devices(
        self,
        admin_user: User,
        data: StationWizardCreate,
        ip_address: str | None = None,
    ) -> tuple[PowerStation, list[StorageDevice]]:
        """在单个事务内原子创建电站 + 关联储能设备。"""

        # 1. 电站名称唯一性检查（乐观检查）
        existing = await self.station_repo.get_by_name(data.name)
        if existing:
            raise BusinessError(
                code="STATION_NAME_DUPLICATE",
                message="电站名称已存在",
                status_code=409,
            )

        # 2. SOC 范围校验（Service 层完整校验，补充 Pydantic 层）
        for device_data in data.storage_devices:
            self._validate_soc_range(
                device_data.soc_lower_limit,
                device_data.soc_upper_limit,
                device_data.name,
            )

        # 3. 创建电站 — C3: 捕获 IntegrityError 处理并发竞态
        station = PowerStation(
            name=data.name,
            province=data.province,
            capacity_mw=data.capacity_mw,
            station_type=data.station_type,
            grid_connection_point=data.grid_connection_point,
            has_storage=data.has_storage,
        )
        try:
            created_station = await self.station_repo.create(station)
        except IntegrityError:
            raise BusinessError(
                code="STATION_NAME_DUPLICATE",
                message="电站名称已存在",
                status_code=409,
            ) from None

        # 4. 审计日志 — 电站创建
        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="create_station",
            resource_type="power_station",
            resource_id=created_station.id,
            changes_after={
                "name": created_station.name,
                "province": created_station.province,
                "capacity_mw": str(created_station.capacity_mw),
                "station_type": created_station.station_type,
                "grid_connection_point": created_station.grid_connection_point,
                "has_storage": created_station.has_storage,
            },
            ip_address=ip_address,
        )

        # 5. M1: 批量创建储能设备（add_all + 单次 flush 减少 DB 往返）
        created_devices: list[StorageDevice] = []
        if data.storage_devices:
            device_objects = [
                StorageDevice(
                    station_id=created_station.id,
                    name=device_data.name,
                    capacity_mwh=device_data.capacity_mwh,
                    max_charge_rate_mw=device_data.max_charge_rate_mw,
                    max_discharge_rate_mw=device_data.max_discharge_rate_mw,
                    soc_upper_limit=device_data.soc_upper_limit,
                    soc_lower_limit=device_data.soc_lower_limit,
                    battery_type=device_data.battery_type,
                )
                for device_data in data.storage_devices
            ]
            # C4: 捕获 IntegrityError 处理设备名称重复
            try:
                self.storage_repo.session.add_all(device_objects)
                await self.storage_repo.session.flush()
            except IntegrityError:
                raise BusinessError(
                    code="DEVICE_NAME_DUPLICATE",
                    message="储能设备名称重复",
                    status_code=422,
                ) from None

            for device in device_objects:
                await self.storage_repo.session.refresh(device)
                created_devices.append(device)

            # H6: 审计日志 — 每个储能设备单独审计（含完整字段）
            for created_device in created_devices:
                await self.audit_service.log_action(
                    user_id=admin_user.id,
                    action="create_storage_device",
                    resource_type="storage_device",
                    resource_id=created_device.id,
                    changes_after={
                        "name": created_device.name,
                        "station_id": str(created_station.id),
                        "capacity_mwh": str(created_device.capacity_mwh),
                        "max_charge_rate_mw": str(created_device.max_charge_rate_mw),
                        "max_discharge_rate_mw": str(created_device.max_discharge_rate_mw),
                        "soc_upper_limit": str(created_device.soc_upper_limit),
                        "soc_lower_limit": str(created_device.soc_lower_limit),
                        "battery_type": created_device.battery_type,
                    },
                    ip_address=ip_address,
                )

        logger.info(
            "wizard_station_created",
            station_name=data.name,
            device_count=len(created_devices),
            admin=admin_user.username,
        )

        return created_station, created_devices

    async def add_device_to_station(
        self,
        admin_user: User,
        station_id: UUID,
        data: StorageDeviceAddInput,
        ip_address: str | None = None,
    ) -> StorageDevice:
        """C2: 向已有电站添加储能设备（业务逻辑在 Service 层）。"""
        # H1: 使用 FOR UPDATE 锁定电站行，防止与 delete_station_device 并发导致 has_storage 不一致
        stmt = select(PowerStation).where(PowerStation.id == station_id).with_for_update()
        result = await self.station_repo.session.execute(stmt)
        station = result.scalar_one_or_none()
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)
        if not station.is_active:
            raise BusinessError(code="STATION_INACTIVE", message="电站已停用，无法添加设备", status_code=409)

        # M4: 单电站设备数量上限（与向导端点的 max_length=50 一致）
        existing_devices = await self.storage_repo.get_by_station_id(station_id)
        if len(existing_devices) >= 50:
            raise BusinessError(
                code="DEVICE_LIMIT_EXCEEDED",
                message="单个电站最多 50 个储能设备",
                status_code=422,
            )

        # SOC 校验
        self._validate_soc_range(data.soc_lower_limit, data.soc_upper_limit, data.name)

        device = StorageDevice(
            station_id=station_id,
            name=data.name,
            capacity_mwh=data.capacity_mwh,
            max_charge_rate_mw=data.max_charge_rate_mw,
            max_discharge_rate_mw=data.max_discharge_rate_mw,
            soc_upper_limit=data.soc_upper_limit,
            soc_lower_limit=data.soc_lower_limit,
            battery_type=data.battery_type,
        )
        try:
            created = await self.storage_repo.create(device)
        except IntegrityError:
            raise BusinessError(
                code="DEVICE_NAME_DUPLICATE",
                message="储能设备名称重复",
                status_code=422,
            ) from None

        # H5+M6: 同步 has_storage 标志并审计
        if not station.has_storage:
            station.has_storage = True
            await self.station_repo.session.flush()
            await self.audit_service.log_action(
                user_id=admin_user.id,
                action="update_station",
                resource_type="power_station",
                resource_id=station_id,
                changes_before={"has_storage": False},
                changes_after={"has_storage": True},
                ip_address=ip_address,
            )

        # H6: 完整审计日志
        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="create_storage_device",
            resource_type="storage_device",
            resource_id=created.id,
            changes_after={
                "name": created.name,
                "station_id": str(station_id),
                "capacity_mwh": str(created.capacity_mwh),
                "max_charge_rate_mw": str(created.max_charge_rate_mw),
                "max_discharge_rate_mw": str(created.max_discharge_rate_mw),
                "soc_upper_limit": str(created.soc_upper_limit),
                "soc_lower_limit": str(created.soc_lower_limit),
                "battery_type": created.battery_type,
            },
            ip_address=ip_address,
        )

        return created

    async def delete_station_device(
        self,
        admin_user: User,
        station_id: UUID,
        device_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """C2: 删除储能设备（软删除，业务逻辑在 Service 层）。"""
        # H5: 锁定电站行（FOR UPDATE），防止并发设备删除导致 has_storage TOCTOU 竞态
        stmt = select(PowerStation).where(PowerStation.id == station_id).with_for_update()
        result = await self.station_repo.session.execute(stmt)
        station = result.scalar_one_or_none()
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)
        if not station.is_active:
            raise BusinessError(code="STATION_INACTIVE", message="电站已停用，无法操作设备", status_code=409)

        device = await self.storage_repo.get_by_id(device_id)
        if not device or device.station_id != station_id:
            raise BusinessError(code="DEVICE_NOT_FOUND", message="储能设备不存在", status_code=404)

        if not device.is_active:
            return

        device.is_active = False
        await self.storage_repo.session.flush()

        # H5+M6: has_storage 同步并审计（在 FOR UPDATE 锁保护下安全更新）
        remaining = await self.storage_repo.get_by_station_id(station_id)
        if not remaining:
            station.has_storage = False
            await self.station_repo.session.flush()
            await self.audit_service.log_action(
                user_id=admin_user.id,
                action="update_station",
                resource_type="power_station",
                resource_id=station_id,
                changes_before={"has_storage": True},
                changes_after={"has_storage": False},
                ip_address=ip_address,
            )

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="delete_storage_device",
            resource_type="storage_device",
            resource_id=device_id,
            changes_before={"is_active": True},
            changes_after={"is_active": False},
            ip_address=ip_address,
        )

    async def update_storage_device(
        self,
        admin_user: User,
        station_id: UUID,
        device_id: UUID,
        update_data: dict,
        ip_address: str | None = None,
    ) -> StorageDevice:
        """更新储能设备参数，支持 SOC 单字段更新时的完整交叉校验。"""

        # 验证电站存在且活跃
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)
        if not station.is_active:
            raise BusinessError(code="STATION_INACTIVE", message="电站已停用，无法更新设备", status_code=409)

        # 验证设备存在且属于该电站且活跃
        device = await self.storage_repo.get_by_id(device_id)
        if not device or device.station_id != station_id:
            raise BusinessError(code="DEVICE_NOT_FOUND", message="储能设备不存在", status_code=404)
        if not device.is_active:
            raise BusinessError(code="DEVICE_INACTIVE", message="储能设备已停用，无法更新", status_code=409)

        # SOC 单字段更新时，合并当前 DB 值做完整交叉校验
        soc_upper = update_data.get("soc_upper_limit", device.soc_upper_limit)
        soc_lower = update_data.get("soc_lower_limit", device.soc_lower_limit)
        if "soc_upper_limit" in update_data or "soc_lower_limit" in update_data:
            self._validate_soc_range(soc_lower, soc_upper, device.name)

        changes_before: dict = {}
        changes_after: dict = {}

        for field, value in update_data.items():
            # H2: 字段白名单，防止 setattr 注入
            if field not in _DEVICE_UPDATE_FIELDS:
                continue
            old_value = getattr(device, field)
            if old_value != value:
                serialized_old = old_value if isinstance(old_value, (bool, int, float, type(None))) else str(old_value)
                serialized_new = value if isinstance(value, (bool, int, float, type(None))) else str(value)
                changes_before[field] = serialized_old
                changes_after[field] = serialized_new
                setattr(device, field, value)

        if changes_after:
            await self.storage_repo.session.flush()
            await self.storage_repo.session.refresh(device)
            await self.audit_service.log_action(
                user_id=admin_user.id,
                action="update_storage_device",
                resource_type="storage_device",
                resource_id=device_id,
                changes_before=changes_before,
                changes_after=changes_after,
                ip_address=ip_address,
            )

        return device
