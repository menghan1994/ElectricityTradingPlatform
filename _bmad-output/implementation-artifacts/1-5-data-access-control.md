# Story 1.5: 数据访问权限控制

Status: done

## Story

As a 系统用户,
I want 系统根据我的角色和绑定关系自动过滤我能看到的数据,
So that 我只能访问权限范围内的信息，符合数据安全要求。

## Acceptance Criteria

1. **Given** 交易员登录后 **When** 访问任何包含电站数据的API端点 **Then** 仅返回该交易员已绑定电站的数据，未绑定电站数据不可见

2. **Given** 储能运维员登录后 **When** 访问储能调度相关API端点 **Then** 仅返回该运维员已绑定储能设备的数据

3. **Given** 交易主管登录后 **When** 访问电站数据API **Then** 可查看所有电站的数据（不受绑定限制）

4. **Given** 高管只读角色用户登录后 **When** 尝试执行写操作（如修改报价、提交确认） **Then** 系统返回403权限不足错误

5. **Given** 未认证用户 **When** 直接访问任何API端点（不携带Token） **Then** 系统返回401未认证错误

## Tasks / Subtasks

- [x] Task 1: 数据访问上下文依赖（核心基础设施）(AC: #1, #2, #3, #4, #5)
  - [x] 1.1 创建 `app/core/data_access.py` — 定义 `DataAccessContext` 数据类（user_id, role, station_ids, device_ids），其中 station_ids/device_ids 为 None 表示"全部可见"
  - [x] 1.2 实现 `get_data_access_context()` FastAPI Dependency — 注入当前用户、角色、绑定关系，按角色决定过滤策略：
    - admin → station_ids=None, device_ids=None（全部可见）
    - trading_manager → station_ids=None, device_ids=None（全部可见）
    - executive_readonly → station_ids=None, device_ids=None（全部可见，写操作在别处拦截）
    - trader → station_ids=从 BindingRepository 查询已绑定电站 ID 列表
    - storage_operator → device_ids=从 BindingRepository 查询已绑定设备 ID 列表
  - [x] 1.3 实现 `require_write_permission()` FastAPI Dependency — 拦截 executive_readonly 角色的写操作，返回 403

- [x] Task 2: Repository 层数据过滤扩展 (AC: #1, #2, #3)
  - [x] 2.1 在 `StationRepository` 添加 `get_all_paginated_filtered()` 方法 — 接受可选 `allowed_station_ids: list[UUID] | None` 参数，为 None 时不过滤，否则 `WHERE id IN (...)` 过滤
  - [x] 2.2 在 `StorageDeviceRepository` 添加 `get_devices_filtered()` 方法 — 接受可选 `allowed_device_ids: list[UUID] | None` 参数，为 None 时不过滤
  - [x] 2.3 在 `StationRepository` 添加 `get_by_id_with_access_check()` 方法 — 获取单个电站时验证用户有权访问

- [x] Task 3: Service 层数据过滤集成 (AC: #1, #2, #3)
  - [x] 3.1 在 `StationService` 添加 `list_stations_for_user()` 方法 — 接受 DataAccessContext，调用 Repository 层的过滤方法
  - [x] 3.2 在 `StationService` 添加 `get_station_for_user()` 方法 — 获取单个电站时验证访问权限，无权返回 `STATION_ACCESS_DENIED`
  - [x] 3.3 创建 `app/services/device_service.py`（如需）或在 `StationService` 中添加设备过滤方法

- [x] Task 4: API 端点权限开放与过滤 (AC: #1, #2, #3, #4, #5)
  - [x] 4.1 修改 `app/api/v1/stations.py` — 电站列表端点从 admin-only 开放为多角色可访问，注入 DataAccessContext 进行数据过滤
  - [x] 4.2 修改 `app/api/v1/stations.py` — 电站详情端点添加访问权限校验
  - [x] 4.3 修改 `app/api/v1/stations.py` — 电站写操作（创建/更新/删除）保持 admin-only + require_write_permission
  - [x] 4.4 修改 `app/api/v1/stations.py` — 储能设备列表端点添加基于设备绑定的过滤
  - [x] 4.5 修改 `app/api/v1/bindings.py` — 绑定管理端点保持 admin-only

- [x] Task 5: 前端权限适配 (AC: #1, #3, #4)
  - [x] 5.1 验证 `src/stores/station.ts` — 已确认电站列表请求无需修改即支持非 admin 角色（后端侧 DataAccessContext 过滤已足够）
  - [x] 5.2 更新 `src/router/index.ts` — 调整路由权限 meta，电站数据相关路由开放给 trader/trading_manager/executive_readonly
  - [x] 5.3 更新 `src/composables/useAuth.ts` 或创建 `src/utils/permission.ts` — 添加权限工具函数（`canWrite()`, `canAccessStation()` 等）
  - [x] 5.4 更新 `src/App.vue` — 侧边栏菜单基于角色动态显示/隐藏（trader 看报价相关、operator 看储能相关、admin 看管理相关）

- [x] Task 6: 后端测试 (AC: #1-#5)
  - [x] 6.1 `tests/unit/core/test_data_access.py` — DataAccessContext 依赖测试（每种角色的过滤策略）
  - [x] 6.2 `tests/unit/repositories/test_station_repository.py` — 添加过滤方法测试（带 allowed_ids / 不带 allowed_ids）
  - [x] 6.3 `tests/unit/services/test_station_service.py` — 添加 list_stations_for_user 测试（各角色场景）
  - [x] 6.4 `tests/integration/api/test_data_access_control.py` — 端到端数据访问控制集成测试：
    - trader 只能看到绑定电站
    - storage_operator 只能看到绑定设备
    - trading_manager 看到所有电站
    - executive_readonly 可读不可写（403）
    - 未认证用户 401
    - admin 全权限

- [x] Task 7: 前端测试 (AC: #1, #4)
  - [x] 7.1 `tests/unit/utils/permission.test.ts` — 权限工具函数测试
  - [x] 7.2 验证 `tests/unit/stores/station.test.ts` — 已确认 store 层无角色特定逻辑变更，权限过滤在后端完成，store 测试无需新增角色场景

## Review Follow-ups (AI)

### R1 Findings (已解决)

#### CRITICAL

- [x] [AI-Review-R1][CRITICAL] `storage_operator` 的 `station_ids=None` 导致后端 API 无限制返回全部电站 — 安全风险，应按绑定设备所属电站过滤 [`api-server/app/core/data_access.py:77-84`]

#### HIGH

- [x] [AI-Review-R1][HIGH] Task 5.1 & 7.2 标记 [x] 但 Git 无变更 — 已更新 Task 描述注明"已验证无需修改"
- [x] [AI-Review-R1][HIGH] `get_station_for_user` 对不存在的电站返回 403 而非 404 — admin 用户查询不存在电站应获得 404，需区分"无权访问"和"不存在"两种场景 [`api-server/app/services/station_service.py:226-241`]
- [x] [AI-Review-R1][HIGH] `require_write_permission` 已实现但未应用于任何写端点 — Task 4.3 要求写操作使用 `require_write_permission`，当前仅依赖 `require_roles(["admin"])` [`api-server/app/api/v1/stations.py:93-127`]

#### MEDIUM

- [x] [AI-Review-R1][MEDIUM] `StationManagementView.vue` 及其测试文件有重大变更但未记录在 File List — 已验证 File List 已包含（在初始实现 Change Log 前补充）
- [x] [AI-Review-R1][MEDIUM] AC #5 集成测试断言 `status_code in (401, 403)` 过弱 — 应精确断言 401 [`api-server/tests/integration/api/test_data_access_control.py:277`]
- [x] [AI-Review-R1][MEDIUM] 未使用的导入 `BusinessError` [`api-server/tests/integration/api/test_data_access_control.py:22`]

#### LOW

- [x] [AI-Review-R1][LOW] `components.d.ts` 自动生成变更未记录在 File List — 已验证 File List 已包含

### R2 Findings (已解决)

#### HIGH

- [x] [AI-Review-R2][HIGH] Trader 通过 API 可无限制访问所有储能设备 — `StorageDeviceRepository.get_all_active_filtered()` 新增 `allowed_station_ids` 参数，`StationService.get_all_active_devices_for_user()` 传入 `access_ctx.station_ids`，trader 设备过滤基于绑定电站

#### MEDIUM

- [x] [AI-Review-R2][MEDIUM] `get_by_id_with_access_check` 是死代码 — 已从 `StationRepository` 移除，同步删除对应单元测试
- [x] [AI-Review-R2][MEDIUM] 集成测试用例名称误导 — `test_station_not_found` 重命名为 `test_station_access_denied`
- [x] [AI-Review-R2][MEDIUM] 缺少 storage_operator 列出电站的集成测试 — 新增 `test_operator_can_list_stations` 和 `TestTraderDeviceAccess` 测试类
- [x] [AI-Review-R2][MEDIUM] 缺少 executive_readonly 角色的前端组件测试 — 新增 `executive_readonly view` 测试组（2 个测试用例）

#### LOW

- [x] [AI-Review-R2][LOW] 多余的 `from __future__ import annotations` — 已移除，改为直接导入 `DataAccessContext`（无循环依赖）
- [x] [AI-Review-R2][LOW] `DataAccessContext.role` 类型为 `str` 而非 `UserRole` — 已改为 `RoleType` Literal 类型
- [x] [AI-Review-R2][LOW] 前后端 storage_operator 电站可见性设计不一致 — 前端 `STATION_VIEW_ROLES` 已添加 `storage_operator`，UI 同步显示电站区域

### R3 Findings (已解决)

#### MEDIUM

- [x] [AI-Review-R3][MEDIUM] `DataAccessContext.station_ids` / `device_ids` 可变列表破坏 frozen 语义 — 字段类型改为 `tuple[UUID, ...] | None`，工厂函数 `get_data_access_context` 中 `list` 转 `tuple()`，Repository 方法参数改为 `Sequence[UUID] | None`，新增 `test_tuple_immutability` 测试验证 `.append()` 抛 `AttributeError`
- [x] [AI-Review-R3][MEDIUM] `get_user_device_station_ids` 查询未过滤已停用设备 — 添加 `.where(StorageDevice.is_active.is_(True))` 条件，已停用设备所属电站不再出现在 operator 的 `station_ids` 中
- [x] [AI-Review-R3][MEDIUM] 缺少 `trading_manager` 和 `storage_operator` 写操作拦截集成测试 — 新增 `TestTradingManagerWriteAccess`（3 测试）和 `TestStorageOperatorWriteAccess`（3 测试），覆盖 POST/PUT/DELETE 均返回 403

#### LOW

- [x] [AI-Review-R3][LOW] 前端 `App.vue` 侧边栏菜单条件冗余 — 简化为 `canViewStation(authStore.user?.role)`，移除冗余的 `canViewDevice` 导入
- [x] [AI-Review-R3][LOW] 前后端设备可见性策略不一致 — `DEVICE_VIEW_ROLES` 添加 `trader`，前后端策略矩阵一致（trader 可见绑定电站下的设备），同步更新 `StationManagementView.test.ts` 和 `permission.test.ts`
- [x] [AI-Review-R3][LOW] 测试辅助方法 `_make_user` 参数类型 `str` 应为 `RoleType` — `test_data_access.py` 两处 `_make_user(role: str)` 改为 `_make_user(role: RoleType)`，`test_data_access_control.py` 的 `_make_user_obj(role: str)` 改为 `_make_user_obj(role: RoleType)`

## Dev Notes

### 核心设计决策

**本 Story 的核心任务是实现基于角色和绑定关系的行级数据过滤机制。** 这是 RBAC 系统的最后一块拼图——前序 Story 已完成认证（1.2）、角色分配（1.3）、绑定配置（1.4），本 Story 让这些安全基础设施真正生效。

**数据访问策略矩阵：**

| 角色 | 电站数据可见范围 | 储能设备可见范围 | 写操作权限 |
|------|----------------|----------------|-----------|
| admin | 全部 | 全部 | 全部 |
| trader | 仅已绑定电站 | 绑定电站下的设备 | 报价相关（Future Epic） |
| storage_operator | 绑定设备所属电站 | 仅已绑定设备 | 调度相关（Future Epic） |
| trading_manager | 全部 | 全部 | 报价+看板相关（Future Epic） |
| executive_readonly | 全部 | 全部 | 无（仅读） |

**设计原则：**
1. **行级过滤在 Repository 层实现** — WHERE 子句条件注入，不在 Python 内存中过滤
2. **DataAccessContext 作为依赖注入** — 避免在每个 Service 方法中重复查询绑定关系
3. **None 语义 = 不过滤** — `allowed_station_ids=None` 意味着全部可见，空列表 `[]` 意味着无权查看任何数据
4. **写权限分离** — executive_readonly 的写操作拦截通过独立 Dependency 实现，不混入数据过滤逻辑
5. **MVP 范围限定** — 本 Story 仅对现有电站/设备端点实施过滤，报价/储能/回测等端点在各自 Epic 中实现时自带过滤

### 技术选型（延续已有方案）

| 库 | 版本 | 说明 |
|---|------|------|
| **FastAPI** | 0.133.x | Dependency 注入实现数据访问上下文 |
| **SQLAlchemy** | 2.0.x | `WHERE ... IN (...)` 过滤条件 + `Mapped[]` 声明式映射 |
| **Pydantic** | 2.x | DataAccessContext 数据校验 |

### DataAccessContext 设计

```python
from dataclasses import dataclass
from uuid import UUID
from app.models.user import UserRole
from app.schemas.user import RoleType

@dataclass(frozen=True)
class DataAccessContext:
    """数据访问上下文 — 通过 FastAPI Dependency 注入到 API 端点"""
    user_id: UUID
    role: RoleType
    station_ids: tuple[UUID, ...] | None  # None = 全部可见, () = 无权查看
    device_ids: tuple[UUID, ...] | None   # None = 全部可见, () = 无权查看

    @property
    def has_full_station_access(self) -> bool:
        """是否有全部电站访问权限（admin/trading_manager/executive_readonly）"""
        return self.station_ids is None

    @property
    def has_full_device_access(self) -> bool:
        """是否有全部设备访问权限（admin）"""
        return self.device_ids is None

    @property
    def is_readonly(self) -> bool:
        """是否为只读角色"""
        return self.role == UserRole.EXECUTIVE_READONLY
```

**Dependency 实现模式（基于现有 dependencies.py 模式扩展）：**

```python
async def get_data_access_context(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> DataAccessContext:
    binding_repo = BindingRepository(session)

    if current_user.role in (UserRole.ADMIN, UserRole.TRADING_MANAGER, UserRole.EXECUTIVE_READONLY):
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=None,  # 全部可见
            device_ids=None,
        )

    if current_user.role == UserRole.TRADER:
        station_ids = await binding_repo.get_user_station_ids(current_user.id)
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=tuple(station_ids),
            device_ids=None,  # trader 不需要设备维度过滤
        )

    if current_user.role == UserRole.STORAGE_OPERATOR:
        device_ids = await binding_repo.get_user_device_ids(current_user.id)
        station_ids = await binding_repo.get_user_device_station_ids(current_user.id)
        return DataAccessContext(
            user_id=current_user.id,
            role=current_user.role,
            station_ids=tuple(station_ids),
            device_ids=tuple(device_ids),
        )

    # 未知角色：零权限（安全降级）+ 日志告警
    logger.warning("unknown_role_zero_access", role=current_user.role, user_id=str(current_user.id))
    return DataAccessContext(
        user_id=current_user.id, role=current_user.role,
        station_ids=(), device_ids=(),
    )
```

### Repository 层过滤模式

**关键：在 SQL 层实现过滤，不在 Python 内存中过滤。**

```python
# StationRepository 新增方法
async def get_all_paginated_filtered(
    self,
    allowed_station_ids: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    province: str | None = None,
    station_type: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[PowerStation], int]:
    stmt = select(PowerStation)
    count_stmt = select(func.count()).select_from(PowerStation)

    # 核心：行级数据过滤
    if allowed_station_ids is not None:
        if len(allowed_station_ids) == 0:
            return [], 0  # 快速返回，无权查看任何电站
        stmt = stmt.where(PowerStation.id.in_(allowed_station_ids))
        count_stmt = count_stmt.where(PowerStation.id.in_(allowed_station_ids))

    # ... 其余过滤条件复用现有逻辑
```

### API 端点权限模型变更

**当前状态（Story 1.4 后）：**
- `GET /api/v1/stations` — admin only
- `POST /api/v1/stations` — admin only
- `PUT /api/v1/stations/{id}` — admin only
- `DELETE /api/v1/stations/{id}` — admin only
- `GET /api/v1/stations/active` — admin only
- `GET /api/v1/stations/devices/active` — admin only
- `GET /api/v1/bindings/{user_id}/*` — admin only
- `PUT /api/v1/bindings/{user_id}/*` — admin only

**Story 1.5 后：**
- `GET /api/v1/stations` — 所有已认证角色（数据按 DataAccessContext 过滤）
- `GET /api/v1/stations/{id}` — 所有已认证角色（验证访问权限）
- `POST /api/v1/stations` — admin only
- `PUT /api/v1/stations/{id}` — admin only
- `DELETE /api/v1/stations/{id}` — admin only
- `GET /api/v1/stations/active` — 所有已认证角色（按绑定过滤）
- `GET /api/v1/stations/devices/active` — 所有已认证角色（按绑定过滤）
- `GET /api/v1/bindings/{user_id}/*` — admin only（不变）
- `PUT /api/v1/bindings/{user_id}/*` — admin only（不变）

### 错误码定义（新增）

| 错误码 | HTTP Status | 含义 |
|--------|-------------|------|
| `STATION_ACCESS_DENIED` | 403 | 用户无权访问该电站 |
| `DEVICE_ACCESS_DENIED` | 403 | 用户无权访问该设备 |
| `WRITE_PERMISSION_DENIED` | 403 | 只读角色无写操作权限 |

### 现有代码基础（必须复用，禁止重写）

**直接复用：**
- `app/core/dependencies.py` — `get_current_user()`, `get_current_active_user()`, `require_roles()`
- `app/core/database.py` — AsyncSession + async_sessionmaker
- `app/core/exceptions.py` — `BusinessError` 异常类
- `app/core/ip_utils.py` — IP 地址工具
- `app/repositories/binding.py` — `BindingRepository.get_user_station_ids()` / `get_user_device_ids()`
- `app/repositories/station.py` — `StationRepository`（扩展新方法）
- `app/repositories/storage.py` — `StorageDeviceRepository`（扩展新方法）
- `app/services/station_service.py` — `StationService`（添加新方法）
- `app/services/audit_service.py` — 审计日志 Service
- `app/api/v1/router.py` — 路由注册
- `web-frontend/src/stores/auth.ts` — 认证状态和角色信息
- `web-frontend/src/api/client.ts` — Axios 实例 + 拦截器（401/403 已处理）

**需要新建的文件：**

后端：
- `api-server/app/core/data_access.py` — DataAccessContext + get_data_access_context + require_write_permission 依赖

前端：
- `web-frontend/src/utils/permission.ts` — 权限工具函数（canWrite, canViewStation 等）

测试：
- `api-server/tests/unit/core/test_data_access.py` — DataAccessContext 单元测试
- `api-server/tests/integration/api/test_data_access_control.py` — 数据访问控制集成测试

**需要修改的文件：**

后端：
- `api-server/app/repositories/station.py` — 添加 get_all_paginated_filtered 方法
- `api-server/app/repositories/storage.py` — 添加设备过滤方法
- `api-server/app/services/station_service.py` — 添加 list_stations_for_user / get_station_for_user 方法
- `api-server/app/api/v1/stations.py` — 开放端点权限 + 注入 DataAccessContext

前端：
- `web-frontend/src/stores/station.ts` — 支持非 admin 角色调用
- `web-frontend/src/router/index.ts` — 调整路由权限 meta
- `web-frontend/src/App.vue` — 侧边栏菜单角色感知

测试：
- `api-server/tests/unit/repositories/test_station_repository.py` — 添加过滤方法测试
- `api-server/tests/unit/services/test_station_service.py` — 添加 for_user 方法测试
- `web-frontend/tests/unit/stores/station.test.ts` — 非 admin 角色测试

### 架构合规要求

**三层架构（强制）：**
```
API 层 (app/api/v1/stations.py)
  → 路由端点，注入 DataAccessContext + require_write_permission
  → 禁止在此层写过滤逻辑

Service 层 (app/services/station_service.py)
  → 接收 DataAccessContext，调用 Repository 层过滤方法
  → 业务规则：角色→过滤策略映射

Repository 层 (app/repositories/station.py + storage.py)
  → SQL WHERE 条件注入实现行级过滤
  → allowed_ids=None → 不添加 IN 条件
  → allowed_ids=[] → 直接返回空结果
```

**命名规范：**
- 新依赖函数：`get_data_access_context`, `require_write_permission`（snake_case，动词开头）
- 新 Repository 方法：`get_all_paginated_filtered`（描述性方法名）
- 新 Service 方法：`list_stations_for_user`, `get_station_for_user`（`_for_user` 后缀表示带权限过滤）
- 新错误码：UPPER_SNAKE_CASE（`STATION_ACCESS_DENIED`）
- 前端权限工具：camelCase（`canWrite()`, `canAccessStation()`）

### 安全注意事项

1. **行级过滤必须在 SQL 层** — 禁止先查全量再 Python 过滤（数据泄露风险 + 性能问题）
2. **空绑定 = 零可见** — trader 未绑定任何电站时，`station_ids=[]`，返回空列表（不报错）
3. **Token 不携带权限详情** — 绑定 ID 列表不编码进 JWT，每次请求实时查询（安全性优先于性能）
4. **executive_readonly 写操作拦截** — 通过独立 Dependency 实现，确保覆盖所有写端点
5. **未认证请求** — 现有 `get_current_user()` 已处理 401 返回，无需额外处理
6. **绑定变更即时生效** — 管理员修改绑定后，交易员下次请求立即反映（因为每次请求实时查询绑定）

### 与前后 Story 的关系

**依赖前序 Story（全部已完成）：**
- Story 1.1: 项目脚手架（FastAPI + Vue + PostgreSQL 基础设施）
- Story 1.2: 用户认证（JWT 双 Token + 会话管理）
- Story 1.3: 用户账户管理（5 角色 RBAC + 审计日志）
- Story 1.4: 交易员-电站绑定（user_station_bindings + user_device_bindings 表 + CRUD）

**为后续 Epic 提供基础：**
- Epic 2 电站配置：电站数据 CRUD 将自动受本 Story 的数据过滤保护
- Epic 5 日前报价：报价端点需注入 DataAccessContext 过滤交易员可见电站
- Epic 6 储能调度：调度端点需注入 DataAccessContext 过滤运维员可见设备
- Epic 8 收益看板：看板数据需基于角色过滤可见电站范围

**本 Story 建立的 DataAccessContext 模式将成为后续所有数据端点的标准权限过滤机制。**

### 从前序 Story 学到的经验教训

**从 Story 1.4（绑定配置）学到的关键教训：**

1. **active_only 过滤**：`get_user_station_ids` 返回的 ID 可能包含已停用电站，必须在 Repository 层同步过滤 `is_active=true`（Story 1.4 Review R2 HIGH-2 修复）
2. **空列表 vs None 语义**：明确区分"没有绑定"（空列表→零可见）和"无需过滤"（None→全部可见），Story 1.4 中 `BindingBatchUpdate` 共享 schema 导致 None vs [] 混淆问题
3. **三层架构严格执行**：Story 1.4 R2 Review 发现多处 API 层直接调 Repository 的问题，必须通过 Service 层中转
4. **测试覆盖要点**：每种角色 × 每个端点的权限矩阵需完整测试，特别是边界情况（trader 无绑定、operator 绑定已停用设备）
5. **前端 403 处理**：Story 1.4 R2 发现前端未处理 `STATION_HAS_BINDINGS` 409 错误，本 Story 需确保前端正确处理 403 权限拒绝
6. **Dependency 注入模式**：使用 `Depends()` 工厂函数而非在每个端点重复查询绑定关系
7. **审计日志**：数据访问过滤本身不需要审计（只是查询），但写操作拦截（403）应考虑是否记录
8. **IP 地址工具**：使用已提取的 `app/core/ip_utils.py` 公共模块，不再在 API 文件中重复

**从 Story 1.3（用户管理）学到的：**

9. **角色常量引用**：使用 `UserRole.ADMIN` 常量而非硬编码字符串 `"admin"`
10. **require_roles 模式**：DataAccessContext 依赖应与 require_roles 组合使用，而非替代

### Git 提交历史分析

最近 5 个提交全部属于 Epic 1：
```
68e44bb Implement trader-station and operator-device binding features  ← Story 1.4
622a988 Implement user account management features                     ← Story 1.3
8f40a18 Update Docker configuration and implement user authentication  ← Story 1.2
09487bc Enhance database configuration and environment setup           ← Story 1.1
71808b3 Add initial configuration files and setup                      ← Story 1.1
```

**代码模式观察：**
- 所有后端代码严格遵循三层架构
- Alembic 迁移使用手写方式（非 autogenerate）
- 前端使用 Pinia Store + API 封装层
- 测试覆盖：unit + integration 两层
- 审计日志在 Service 层统一处理

### Project Structure Notes

- 新增核心文件 `app/core/data_access.py` 位于 `app/core/` 框架基础设施目录
- 前端权限工具 `src/utils/permission.ts` 位于工具函数目录
- 测试文件遵循镜像源码结构原则
- 不引入新的 npm 或 pip 依赖

### References

- [Source: architecture.md#Authentication & Security] — RBAC + 资源级权限、数据行级过滤设计
- [Source: architecture.md#Data Architecture] — PostgreSQL public Schema、Repository Pattern
- [Source: architecture.md#Implementation Patterns] — 三层架构、命名规范、反模式清单
- [Source: architecture.md#Enforcement Guidelines] — AI Agent 必须遵守的 8 条规则
- [Source: epics/epic-1.md#Story 1.5] — 原始需求和验收标准（5 条 AC）
- [Source: prd/functional-requirements.md#FR33] — 按角色和电站绑定关系控制数据访问
- [Source: prd/non-functional-requirements.md#NFR8] — 会话超时和认证策略
- [Source: project-context.md#Framework-Specific Rules] — FastAPI 三层架构强制、RBAC 依赖注入
- [Source: project-context.md#Critical Implementation Rules] — 反模式清单、安全规则
- [Source: 1-4-trader-station-binding.md] — 绑定表结构、API 端点设计、Review 经验教训（6 轮 Review）
- [Source: 1-4-trader-station-binding.md#API 端点设计] — 绑定端点前缀 `/bindings`（非 `/users`）
- [Source: ux-design-specification.md#Target Users] — 5 种角色的使用场景和权限需求

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

无需调试日志。

### Completion Notes List

- 实现了 DataAccessContext 冻结数据类及两个 FastAPI Dependency（get_data_access_context, require_write_permission）
- Repository 层新增 WHERE IN 过滤方法，SQL 层行级过滤（非 Python 内存过滤）
- Service 层新增 `_for_user` 后缀方法，接受 DataAccessContext 进行权限过滤
- API 读端点从 admin-only 开放为多角色可访问，写端点保持 admin-only
- 前端新增 permission.ts 权限工具函数，路由和侧边栏菜单基于角色动态控制
- 后端测试 229 全通过（含 62+ 新增/修改测试），前端测试 92 全通过（含 16 新增测试）
- 修复了 test_devices.py 回归问题：端点签名变更后需更新 mock 策略
- ✅ Resolved review finding [CRITICAL]: `storage_operator` 的 `station_ids=None` 安全漏洞 — 新增 `BindingRepository.get_user_device_station_ids()` 方法，通过 JOIN storage_devices 表获取绑定设备所属电站 ID 列表
- ✅ Resolved review finding [HIGH]: `get_station_for_user` 403/404 混淆 — 重构为先查电站存在性(404)，再检查访问权限(403)
- ✅ Resolved review finding [HIGH]: `require_write_permission` 未应用 — 已添加到 POST/PUT/DELETE 三个写端点的 Depends 参数
- ✅ Resolved review finding [HIGH]: Task 5.1 & 7.2 虚假完成 — 已更新 Task 描述为"已验证无需修改"
- ✅ Resolved review finding [MEDIUM]: AC#5 断言过弱 — 精确断言 `status_code == 401`
- ✅ Resolved review finding [MEDIUM]: 移除未使用的 `BusinessError` 导入
- ✅ Resolved review finding [MEDIUM/LOW]: File List 已包含 StationManagementView 和 components.d.ts（验证无需修改）
- 后端测试 230 全通过，前端测试 97 全通过
- ✅ Resolved R2 review finding [HIGH]: Trader 设备 API 无限制访问 — `StorageDeviceRepository.get_all_active_filtered()` 新增 `allowed_station_ids` 参数，设备过滤基于电站绑定
- ✅ Resolved R2 review finding [MEDIUM]: 移除死代码 `get_by_id_with_access_check`（从 StationRepository 和对应测试中删除）
- ✅ Resolved R2 review finding [MEDIUM]: 重命名 `test_station_not_found` → `test_station_access_denied`
- ✅ Resolved R2 review finding [MEDIUM]: 新增 storage_operator 电站列表集成测试和 trader 设备过滤集成测试
- ✅ Resolved R2 review finding [MEDIUM]: 新增 executive_readonly 前端组件测试（可见性 + 无操作按钮）
- ✅ Resolved R2 review finding [LOW]: 移除 `from __future__ import annotations`，改为直接导入
- ✅ Resolved R2 review finding [LOW]: `DataAccessContext.role` 类型改为 `RoleType` Literal
- ✅ Resolved R2 review finding [LOW]: 前端 `STATION_VIEW_ROLES` 添加 `storage_operator`，前后端一致
- 后端测试 230 全通过，前端测试 100 全通过
- ✅ Resolved R3 review finding [MEDIUM]: DataAccessContext `list` → `tuple`，frozen 语义完整不可变
- ✅ Resolved R3 review finding [MEDIUM]: `get_user_device_station_ids` 添加 `is_active=True` 过滤
- ✅ Resolved R3 review finding [MEDIUM]: 新增 trading_manager/storage_operator 写操作拦截集成测试（6 个测试）
- ✅ Resolved R3 review finding [LOW]: App.vue 侧边栏条件简化（移除冗余 `canViewDevice`）
- ✅ Resolved R3 review finding [LOW]: `DEVICE_VIEW_ROLES` 添加 `trader`，前后端策略一致
- ✅ Resolved R3 review finding [LOW]: 测试辅助方法参数类型 `str` → `RoleType`
- 后端测试 237 全通过，前端测试 100 全通过
- ✅ Resolved R4 review finding [MEDIUM]: require_write_permission 集成测试未真正触发 — 新增结构性反射测试验证依赖确实挂载在所有写端点
- ✅ Resolved R4 review finding [MEDIUM]: 未知角色安全降级缺少日志 — 添加 logger.warning("unknown_role_zero_access")
- ✅ Resolved R4 review finding [MEDIUM]: get_station_for_user O(n) tuple 查找 — 添加设计注释说明单次查找+典型 n<50 无需 frozenset
- ✅ Resolved R4 review finding [LOW]: test_devices.py DataAccessContext station_ids list→tuple
- ✅ Resolved R4 review finding [LOW]: test_stations.py _make_data_access_context 未转 tuple — 添加 tuple() 转换
- ✅ Resolved R4 review finding [LOW]: test_stations.py _make_user_obj(role: str) → RoleType
- ✅ Resolved R4 review finding [LOW]: Story Dev Notes DataAccessContext 示例同步（list→tuple、str→UserRole）
- ✅ Resolved R4 review finding [LOW]: trading_manager/storage_operator 写操作集成测试添加错误码 FORBIDDEN 断言
- 后端测试 238 全通过，前端测试 100 全通过

### File List

**新增文件：**
- `api-server/app/core/data_access.py` — DataAccessContext + get_data_access_context + require_write_permission
- `web-frontend/src/utils/permission.ts` — 前端权限工具函数（canWrite, canViewStation, canViewDevice, isAdmin）
- `api-server/tests/unit/core/__init__.py` — 测试目录 init
- `api-server/tests/unit/core/test_data_access.py` — DataAccessContext 单元测试（18 个测试）
- `api-server/tests/integration/api/test_data_access_control.py` — 数据访问控制集成测试（16 个测试）
- `web-frontend/tests/unit/utils/permission.test.ts` — 权限工具函数测试（16 个测试）

**修改文件：**
- `api-server/app/repositories/binding.py` — 新增 get_user_device_station_ids（JOIN 查询设备所属电站）
- `api-server/app/repositories/station.py` — 新增 get_all_paginated_filtered, get_all_active_filtered；移除死代码 get_by_id_with_access_check
- `api-server/app/repositories/storage.py` — get_all_active_filtered 新增 allowed_station_ids 参数
- `api-server/app/services/station_service.py` — 新增 list_stations_for_user, get_station_for_user（区分 404/403）, get_all_active_stations_for_user, get_all_active_devices_for_user（传入 station_ids）；移除多余的 future annotations 导入；改为直接导入 DataAccessContext
- `api-server/app/core/data_access.py` — role 字段类型从 str 改为 RoleType
- `api-server/app/api/v1/stations.py` — 读端点使用 DataAccessContext 替代 require_roles，写端点添加 require_write_permission
- `web-frontend/src/router/index.ts` — StationManagement 路由开放给多角色
- `web-frontend/src/App.vue` — 侧边栏菜单基于角色动态显隐
- `api-server/tests/unit/repositories/test_station_repository.py` — 移除 TestGetByIdWithAccessCheck 测试类
- `api-server/tests/unit/services/test_station_service.py` — 新增 trader 设备过滤测试、更新 operator 测试传入 station_ids、更新 allowed_station_ids 断言
- `api-server/tests/integration/api/test_stations.py` — 重命名 test_station_not_found → test_station_access_denied
- `api-server/tests/integration/api/test_devices.py` — 适配 DataAccessContext 端点变更
- `web-frontend/src/views/admin/StationManagementView.vue` — 添加角色感知 UI 渲染
- `web-frontend/tests/unit/views/StationManagementView.test.ts` — 新增 storage_operator 电站可见性/executive_readonly 可见性和无操作按钮测试
- `web-frontend/tests/unit/utils/permission.test.ts` — 更新 storage_operator canViewStation 断言为 true
- `web-frontend/components.d.ts` — unplugin-vue-components 自动生成更新

## Change Log

| 日期 | 变更内容 | 原因 |
|------|---------|------|
| 2026-02-28 | 完成全部 7 个 Task 的实现 | Story 1.5 初始实现 |
| 2026-02-28 | 修复 test_devices.py 回归 | API 端点从 require_roles 改为 get_data_access_context 后测试需同步更新 |
| 2026-02-28 | Code Review R1: 发现 1C/3H/3M/1L 问题，创建 Action Items | 安全风险(storage_operator全站访问)、错误码混淆(403/404)、未使用的依赖、File List 不完整 |
| 2026-02-28 | Addressed code review R1 findings — 8 items resolved | CRITICAL: storage_operator电站过滤修复; HIGH: 403/404区分、write_permission应用、Task描述修正; MEDIUM: 断言精确化、导入清理; LOW: File List验证 |
| 2026-02-28 | Code Review R2: 发现 1H/4M/3L 问题，创建 Action Items | 安全风险(trader设备API无限制)、死代码(get_by_id_with_access_check)、测试覆盖缺口(storage_operator电站/executive_readonly前端)、代码规范(future annotations/类型安全) |
| 2026-02-28 | Addressed code review R2 findings — 8 items resolved | HIGH: trader设备过滤基于station_ids; MEDIUM: 删除死代码、修正测试名称、补充测试覆盖; LOW: 移除future annotations、role类型改为RoleType、前端storage_operator电站可见性一致 |
| 2026-02-28 | Code Review R3: 发现 0H/3M/3L 问题，创建 Action Items | 防御性编程(frozen列表可变性)、设备过滤(已停用设备电站可见)、测试覆盖(trading_manager写操作)、代码规范(冗余条件/类型安全/文档一致性) |
| 2026-02-28 | Addressed code review R3 findings — 6 items resolved | MEDIUM: DataAccessContext list→tuple不可变性、已停用设备电站过滤、trading_manager/operator写操作测试; LOW: App.vue条件简化、DEVICE_VIEW_ROLES添加trader、测试类型RoleType |
| 2026-02-28 | Code Review R4: 发现 0H/3M/5L 问题，全部修复 | 测试覆盖(require_write_permission未真正触发)、安全(未知角色降级无日志)、性能(O(n)tuple查找)、类型一致性(list→tuple/str→RoleType)、文档同步 |
| 2026-02-28 | Addressed code review R4 findings — 8 items resolved | M1: 结构性反射测试验证write_permission挂载; M2: 未知角色logger.warning; M3: O(n)设计注释(单次查找/典型n<50); L1-L5: test_devices/test_stations类型修正、Dev Notes同步、错误码断言 |
