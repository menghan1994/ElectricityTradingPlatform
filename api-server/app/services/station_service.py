from uuid import UUID

import structlog

from app.core.data_access import DataAccessContext
from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.models.user import User
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.schemas.station import StationCreate, StationUpdate
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class StationService:
    def __init__(
        self,
        station_repo: StationRepository,
        audit_service: AuditService,
        storage_repo: StorageDeviceRepository | None = None,
    ):
        self.station_repo = station_repo
        self.audit_service = audit_service
        self.storage_repo = storage_repo

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    async def create_station(
        self, admin_user: User, data: StationCreate, ip_address: str | None = None,
    ) -> PowerStation:
        self._warn_if_no_ip("create_station", ip_address)

        existing = await self.station_repo.get_by_name(data.name)
        if existing:
            raise BusinessError(code="STATION_NAME_EXISTS", message="电站名称已存在", status_code=409)

        station = PowerStation(
            name=data.name,
            province=data.province,
            capacity_mw=data.capacity_mw,
            station_type=data.station_type,
            has_storage=data.has_storage,
        )
        created = await self.station_repo.create(station)

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="create_station",
            resource_type="power_station",
            resource_id=created.id,
            changes_after={
                "name": created.name,
                "province": created.province,
                "capacity_mw": str(created.capacity_mw),
                "station_type": created.station_type,
                "has_storage": created.has_storage,
            },
            ip_address=ip_address,
        )

        logger.info("station_created", station_name=data.name, admin=admin_user.username)
        return created

    async def update_station(
        self, admin_user: User, station_id: UUID, data: StationUpdate, ip_address: str | None = None,
    ) -> PowerStation:
        self._warn_if_no_ip("update_station", ip_address)

        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)

        update_data = data.model_dump(exclude_unset=True)

        # HIGH-1: is_active 变更时需检查绑定关系（与 delete_station 一致的保护逻辑）
        if "is_active" in update_data and update_data["is_active"] is False and station.is_active:
            if await self.station_repo.has_active_bindings(station_id):
                raise BusinessError(
                    code="STATION_HAS_BINDINGS",
                    message="电站有活跃绑定关系，无法停用",
                    status_code=409,
                )

        if "name" in update_data and update_data["name"] != station.name:
            existing = await self.station_repo.get_by_name(update_data["name"])
            if existing:
                raise BusinessError(code="STATION_NAME_EXISTS", message="电站名称已存在", status_code=409)

        changes_before: dict = {}
        changes_after: dict = {}

        for field, value in update_data.items():
            old_value = getattr(station, field)
            if old_value != value:
                # MEDIUM: 正确序列化值类型，避免 hasattr(__str__) 恒为 True
                serialized_old = old_value if isinstance(old_value, (bool, int, float, type(None))) else str(old_value)
                serialized_new = value if isinstance(value, (bool, int, float, type(None))) else str(value)
                changes_before[field] = serialized_old
                changes_after[field] = serialized_new
                setattr(station, field, value)

        if changes_after:
            await self.station_repo.session.flush()
            await self.station_repo.session.refresh(station)
            await self.audit_service.log_action(
                user_id=admin_user.id,
                action="update_station",
                resource_type="power_station",
                resource_id=station_id,
                changes_before=changes_before,
                changes_after=changes_after,
                ip_address=ip_address,
            )
            logger.info("station_updated", station_name=station.name, changes=list(changes_after.keys()), admin=admin_user.username)

        return station

    async def delete_station(
        self, admin_user: User, station_id: UUID, ip_address: str | None = None,
    ) -> None:
        """软删除电站：设 is_active = false"""
        self._warn_if_no_ip("delete_station", ip_address)

        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)

        # 已停用的电站无需再次停用
        if not station.is_active:
            return

        if await self.station_repo.has_active_bindings(station_id):
            raise BusinessError(code="STATION_HAS_BINDINGS", message="电站有活跃绑定关系，无法停用", status_code=409)

        station.is_active = False
        await self.station_repo.session.flush()

        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="delete_station",
            resource_type="power_station",
            resource_id=station_id,
            changes_before={"is_active": True},
            changes_after={"is_active": False},
            ip_address=ip_address,
        )

        logger.info("station_deactivated", station_name=station.name, admin=admin_user.username)

    async def get_station(self, station_id: UUID) -> PowerStation:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise BusinessError(code="STATION_NOT_FOUND", message="电站不存在", status_code=404)
        return station

    async def list_stations(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        province: str | None = None,
        station_type: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PowerStation], int]:
        return await self.station_repo.get_all_paginated(
            page, page_size, search, province, station_type, is_active=is_active,
        )

    async def get_all_active_stations(self) -> list[PowerStation]:
        return await self.station_repo.get_all_active()

    async def get_all_active_devices(self) -> list[StorageDevice]:
        """通过 Service 层获取活跃设备，避免 API 层直接实例化 Repository。"""
        if not self.storage_repo:
            raise RuntimeError("StorageDeviceRepository not injected")
        return await self.storage_repo.get_all_active()

    async def get_all_active_devices_with_station_names(
        self,
    ) -> tuple[list[StorageDevice], dict[str, str]]:
        """获取所有活跃设备及其关联电站名称映射，避免 API 层组装逻辑。"""
        if not self.storage_repo:
            raise RuntimeError("StorageDeviceRepository not injected")
        devices = await self.storage_repo.get_all_active()
        if not devices:
            return [], {}
        # 仅查询设备引用的电站，避免全表扫描所有活跃电站
        referenced_station_ids = list({d.station_id for d in devices})
        stations = await self.station_repo.get_by_ids(referenced_station_ids)
        station_name_map = {str(s.id): s.name for s in stations}
        return devices, station_name_map

    # ── 带数据访问控制的方法 ──

    async def list_stations_for_user(
        self,
        access_ctx: DataAccessContext,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        province: str | None = None,
        station_type: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[PowerStation], int]:
        """按用户权限过滤的电站列表查询。"""
        return await self.station_repo.get_all_paginated_filtered(
            allowed_station_ids=access_ctx.station_ids,
            page=page,
            page_size=page_size,
            search=search,
            province=province,
            station_type=station_type,
            is_active=is_active,
        )

    async def get_station_for_user(
        self,
        access_ctx: DataAccessContext,
        station_id: UUID,
    ) -> PowerStation:
        """获取单个电站，验证用户有权访问。

        区分两种错误场景：
        - 电站不存在 → 404 STATION_NOT_FOUND
        - 电站存在但无权访问 → 403 STATION_ACCESS_DENIED
        """
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise BusinessError(
                code="STATION_NOT_FOUND",
                message="电站不存在",
                status_code=404,
            )
        # O(n) on tuple: 单次查找/请求，典型 n < 50，无需 frozenset
        if access_ctx.station_ids is not None and station_id not in access_ctx.station_ids:
            raise BusinessError(
                code="STATION_ACCESS_DENIED",
                message="无权访问该电站",
                status_code=403,
            )
        return station

    async def get_all_active_stations_for_user(
        self,
        access_ctx: DataAccessContext,
    ) -> list[PowerStation]:
        """按用户权限过滤的活跃电站列表。"""
        return await self.station_repo.get_all_active_filtered(
            allowed_station_ids=access_ctx.station_ids,
        )

    async def get_all_active_devices_for_user(
        self,
        access_ctx: DataAccessContext,
    ) -> tuple[list[StorageDevice], dict[str, str]]:
        """按用户权限过滤的活跃设备列表（含电站名称映射）。

        过滤逻辑：
        - admin/trading_manager/executive_readonly → device_ids=None, station_ids=None → 全部
        - trader → device_ids=None, station_ids=[绑定电站] → 仅绑定电站下的设备
        - storage_operator → device_ids=[绑定设备], station_ids=[设备所属电站] → 仅绑定设备
        """
        if not self.storage_repo:
            raise RuntimeError("StorageDeviceRepository not injected")
        devices = await self.storage_repo.get_all_active_filtered(
            allowed_device_ids=access_ctx.device_ids,
            allowed_station_ids=access_ctx.station_ids,
        )
        if not devices:
            return [], {}
        referenced_station_ids = list({d.station_id for d in devices})
        stations = await self.station_repo.get_by_ids(referenced_station_ids)
        station_name_map = {str(s.id): s.name for s in stations}
        return devices, station_name_map
