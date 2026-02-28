from uuid import UUID

import structlog

from app.core.exceptions import BusinessError
from app.models.station import PowerStation
from app.models.storage import StorageDevice
from app.models.user import User, UserRole
from app.repositories.binding import BindingRepository
from app.repositories.station import StationRepository
from app.repositories.storage import StorageDeviceRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class BindingService:
    def __init__(
        self,
        binding_repo: BindingRepository,
        station_repo: StationRepository,
        storage_repo: StorageDeviceRepository,
        user_repo: UserRepository,
        audit_service: AuditService,
    ):
        self.binding_repo = binding_repo
        self.station_repo = station_repo
        self.storage_repo = storage_repo
        self.user_repo = user_repo
        self.audit_service = audit_service

    def _warn_if_no_ip(self, action: str, ip_address: str | None) -> None:
        if ip_address is None:
            logger.warning("audit_ip_missing", action=action, hint="非 HTTP 上下文调用，IP 地址缺失")

    async def _validate_user(self, user_id: UUID, *, check_status: bool = False) -> User:
        """校验用户存在性。check_status=True 时额外检查 is_active 和 is_locked。"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise BusinessError(code="USER_NOT_FOUND", message="用户不存在", status_code=404)
        if check_status:
            if not user.is_active:
                raise BusinessError(code="USER_INACTIVE", message="用户已停用，无法绑定资源", status_code=422)
            if user.is_locked:
                raise BusinessError(code="USER_LOCKED", message="用户已锁定，无法绑定资源", status_code=422)
        return user

    async def get_user_station_bindings(self, user_id: UUID) -> tuple[list[UUID], list[PowerStation]]:
        """返回 (station_ids, stations) — station_ids 仅包含活跃电站"""
        await self._validate_user(user_id)
        station_ids = await self.binding_repo.get_user_station_ids(user_id)
        if not station_ids:
            return [], []
        stations = await self.station_repo.get_by_ids(station_ids, active_only=True)
        # HIGH-2: 统一过滤 — station_ids 与 stations 保持一致
        active_ids = [s.id for s in stations]
        return active_ids, stations

    async def get_user_device_bindings(self, user_id: UUID) -> tuple[list[UUID], list[StorageDevice]]:
        """返回 (device_ids, devices) — device_ids 仅包含活跃设备"""
        await self._validate_user(user_id)
        device_ids = await self.binding_repo.get_user_device_ids(user_id)
        if not device_ids:
            return [], []
        devices = await self.storage_repo.get_by_ids(device_ids, active_only=True)
        active_ids = [d.id for d in devices]
        return active_ids, devices

    async def update_user_station_bindings(
        self,
        admin_user: User,
        user_id: UUID,
        station_ids: list[UUID],
        ip_address: str | None = None,
    ) -> tuple[list[UUID], list[PowerStation]]:
        self._warn_if_no_ip("update_station_bindings", ip_address)

        # HIGH-6: 校验目标用户状态（is_active / is_locked）
        target_user = await self._validate_user(user_id, check_status=True)
        if target_user.role != UserRole.TRADER:
            raise BusinessError(
                code="ROLE_BINDING_MISMATCH",
                message="仅交易员(trader)可绑定电站",
                status_code=422,
            )

        # HIGH-3: 去重 ID，避免唯一约束冲突导致 500
        station_ids = list(dict.fromkeys(station_ids))

        # 校验所有电站存在且激活
        if station_ids:
            all_stations = await self.station_repo.get_by_ids(station_ids)
            all_found_ids = {s.id for s in all_stations}
            missing = set(station_ids) - all_found_ids
            if missing:
                raise BusinessError(
                    code="STATION_NOT_FOUND",
                    message="部分电站不存在",
                    detail={"missing_ids": [str(sid) for sid in missing]},
                    status_code=404,
                )
            inactive = [s for s in all_stations if not s.is_active]
            if inactive:
                raise BusinessError(
                    code="STATION_NOT_FOUND",
                    message="部分电站已停用",
                    detail={"inactive_ids": [str(s.id) for s in inactive]},
                    status_code=404,
                )

        # 获取变更前的绑定（FOR UPDATE 防止并发更新竞态）
        old_station_ids = await self.binding_repo.get_user_station_ids(
            user_id, for_update=True,
        )

        # 执行全量替换
        await self.binding_repo.replace_user_station_bindings(user_id, station_ids)

        # 审计日志
        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="update_station_bindings",
            resource_type="user_station_binding",
            resource_id=user_id,
            changes_before={"station_ids": [str(sid) for sid in old_station_ids]},
            changes_after={"station_ids": [str(sid) for sid in station_ids]},
            ip_address=ip_address,
        )

        logger.info(
            "station_bindings_updated",
            target_user=target_user.username,
            old_count=len(old_station_ids),
            new_count=len(station_ids),
            admin=admin_user.username,
        )

        # 复用验证阶段已获取的 stations（已确认全部 active），避免冗余 DB 查询
        validated_stations: list[PowerStation] = all_stations if station_ids else []
        result_ids = [s.id for s in validated_stations]
        return result_ids, validated_stations

    async def update_user_device_bindings(
        self,
        admin_user: User,
        user_id: UUID,
        device_ids: list[UUID],
        ip_address: str | None = None,
    ) -> tuple[list[UUID], list[StorageDevice]]:
        self._warn_if_no_ip("update_device_bindings", ip_address)

        # HIGH-6: 校验目标用户状态
        target_user = await self._validate_user(user_id, check_status=True)
        if target_user.role != UserRole.STORAGE_OPERATOR:
            raise BusinessError(
                code="ROLE_BINDING_MISMATCH",
                message="仅储能运维员(storage_operator)可绑定设备",
                status_code=422,
            )

        # HIGH-3: 去重 ID
        device_ids = list(dict.fromkeys(device_ids))

        # 校验所有设备存在且激活
        if device_ids:
            all_devices = await self.storage_repo.get_by_ids(device_ids)
            all_found_ids = {d.id for d in all_devices}
            missing = set(device_ids) - all_found_ids
            if missing:
                raise BusinessError(
                    code="DEVICE_NOT_FOUND",
                    message="部分储能设备不存在",
                    detail={"missing_ids": [str(did) for did in missing]},
                    status_code=404,
                )
            inactive = [d for d in all_devices if not d.is_active]
            if inactive:
                raise BusinessError(
                    code="DEVICE_NOT_FOUND",
                    message="部分储能设备已停用",
                    detail={"inactive_ids": [str(d.id) for d in inactive]},
                    status_code=404,
                )

        # 获取变更前的绑定（FOR UPDATE 防止并发更新竞态）
        old_device_ids = await self.binding_repo.get_user_device_ids(
            user_id, for_update=True,
        )

        # 执行全量替换
        await self.binding_repo.replace_user_device_bindings(user_id, device_ids)

        # 审计日志
        await self.audit_service.log_action(
            user_id=admin_user.id,
            action="update_device_bindings",
            resource_type="user_device_binding",
            resource_id=user_id,
            changes_before={"device_ids": [str(did) for did in old_device_ids]},
            changes_after={"device_ids": [str(did) for did in device_ids]},
            ip_address=ip_address,
        )

        logger.info(
            "device_bindings_updated",
            target_user=target_user.username,
            old_count=len(old_device_ids),
            new_count=len(device_ids),
            admin=admin_user.username,
        )

        # 复用验证阶段已获取的 devices（已确认全部 active），避免冗余 DB 查询
        validated_devices: list[StorageDevice] = all_devices if device_ids else []
        result_ids = [d.id for d in validated_devices]
        return result_ids, validated_devices
