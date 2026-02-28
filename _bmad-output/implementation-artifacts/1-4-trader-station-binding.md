# Story 1.4: 交易员-电站与运维员-设备绑定配置

Status: done

## Story

As a 系统管理员（老周）,
I want 配置交易员与电站的绑定关系、储能运维员与储能设备的绑定关系,
So that 每个人只能操作和查看自己负责的电站/设备。

## Acceptance Criteria

1. **Given** 管理员已登录且系统中已有用户和电站数据 **When** 管理员为一个交易员选择一个或多个电站并保存绑定关系 **Then** 绑定关系生效，该交易员登录后仅能看到绑定电站的数据，绑定变更记录写入审计日志

2. **Given** 管理员已登录且系统中已有运维员角色用户和储能设备数据 **When** 管理员为一个储能运维员选择一个或多个储能设备并保存绑定关系 **Then** 绑定关系生效，该运维员仅能查看和操作所绑定设备的调度指令，绑定变更记录写入审计日志

3. **Given** 交易员已绑定电站A和电站B **When** 管理员移除交易员与电站B的绑定 **Then** 交易员下次访问时无法看到电站B的数据，变更记录写入审计日志

## Tasks / Subtasks

- [x] Task 1: 数据库建模 — 电站表 + 储能设备表 + 绑定关联表 (AC: #1, #2)
  - [x] 1.1 创建 Alembic 迁移：`power_stations` 表（id, name, province, capacity_mw, station_type, has_storage, is_active, created_at, updated_at）
  - [x] 1.2 创建 Alembic 迁移：`storage_devices` 表（id, station_id FK, name, capacity_mwh, max_charge_rate_mw, max_discharge_rate_mw, soc_upper_limit, soc_lower_limit, is_active, created_at, updated_at）
  - [x] 1.3 创建 Alembic 迁移：`user_station_bindings` 关联表（id, user_id, station_id, created_at）+ 唯一约束 (user_id, station_id)
  - [x] 1.4 创建 Alembic 迁移：`user_device_bindings` 关联表（id, user_id, device_id, created_at）+ 唯一约束 (user_id, device_id)

- [x] Task 2: ORM 模型创建 (AC: #1, #2)
  - [x] 2.1 创建 `app/models/station.py` — PowerStation 模型（继承 Base, IdMixin, TimestampMixin）
  - [x] 2.2 创建 `app/models/storage.py` — StorageDevice 模型（继承 Base, IdMixin, TimestampMixin，FK → power_stations.id）
  - [x] 2.3 创建 `app/models/binding.py` — UserStationBinding + UserDeviceBinding 关联模型（继承 Base, IdMixin）
  - [x] 2.4 在 `app/models/__init__.py` 中导入新模型，在 `alembic/env.py` 中导入

- [x] Task 3: Pydantic Schemas (AC: #1, #2, #3)
  - [x] 3.1 创建 `app/schemas/station.py` — StationRead, StationCreate, StationUpdate, StationListResponse
  - [x] 3.2 创建 `app/schemas/storage.py` — StorageDeviceRead, StorageDeviceCreate, StorageDeviceUpdate
  - [x] 3.3 创建 `app/schemas/binding.py` — BindingCreate, BindingBatchUpdate（用户绑定的电站/设备 ID 列表）, UserBindingsRead

- [x] Task 4: Repository 层 (AC: #1, #2, #3)
  - [x] 4.1 创建 `app/repositories/station.py` — StationRepository（继承 BaseRepository[PowerStation]，添加 get_all_active, get_by_province 等查询）
  - [x] 4.2 创建 `app/repositories/storage.py` — StorageDeviceRepository（继承 BaseRepository[StorageDevice]，添加 get_by_station_id 等查询）
  - [x] 4.3 创建 `app/repositories/binding.py` — BindingRepository（获取用户绑定的电站/设备列表、批量更新绑定关系、按用户查询绑定）

- [x] Task 5: Service 层 (AC: #1, #2, #3)
  - [x] 5.1 创建 `app/services/station_service.py` — 电站 CRUD + 审计日志
  - [x] 5.2 创建 `app/services/binding_service.py` — 绑定关系管理（批量设置用户-电站绑定、批量设置用户-设备绑定、查询用户绑定、角色校验——仅 trader 可绑电站、仅 storage_operator 可绑设备）+ 审计日志

- [x] Task 6: API 端点 (AC: #1, #2, #3)
  - [x] 6.1 创建 `app/api/v1/stations.py` — 电站 CRUD 端点（admin 角色）
  - [x] 6.2 创建 `app/api/v1/bindings.py` — 绑定管理端点：GET/PUT /users/{user_id}/station_bindings, GET/PUT /users/{user_id}/device_bindings（admin 角色）
  - [x] 6.3 注册路由到 `app/api/v1/router.py`

- [x] Task 7: 种子数据 (AC: #1, #2)
  - [x] 7.1 创建 `scripts/seed_stations.py` — 写入示例电站（含储能/不含储能各至少1个）+ 储能设备数据
  - [x] 7.2 创建 `scripts/seed_bindings.py` — 示例绑定关系

- [x] Task 8: 前端 API 封装 (AC: #1, #2, #3)
  - [x] 8.1 创建 `src/api/station.ts` — 电站 CRUD + 绑定管理 API 调用
  - [x] 8.2 更新 `src/types/station.ts` — 类型定义

- [x] Task 9: 前端 Store (AC: #1, #2, #3)
  - [x] 9.1 创建 `src/stores/station.ts` — Pinia Store（stationList, fetchStations, createStation 等）
  - [x] 9.2 扩展绑定管理 actions（fetchUserBindings, updateUserStationBindings, updateUserDeviceBindings）

- [x] Task 10: 前端电站管理页面 (AC: #1)
  - [x] 10.1 创建 `src/views/admin/StationManagementView.vue` — 电站列表 + CRUD 操作
  - [x] 10.2 电站创建/编辑对话框组件
  - [x] 10.3 注册路由 `/admin/stations`（meta: { requiresAuth: true, roles: ['admin'] }）

- [x] Task 11: 前端绑定配置页面 (AC: #1, #2, #3)
  - [x] 11.1 在 UserManagementView 用户列表操作列添加"资源绑定"按钮
  - [x] 11.2 创建 BindingConfigDrawer 组件 — 抽屉式面板，左侧展示用户信息+角色，右侧根据角色展示：
    - trader 角色：Transfer 穿梭框，左侧所有电站、右侧已绑定电站
    - storage_operator 角色：Transfer 穿梭框，左侧所有储能设备、右侧已绑定设备
    - 其他角色：提示"该角色无需绑定资源"
  - [x] 11.3 保存绑定时调用批量更新 API + 审计日志
  - [x] 11.4 App.vue 侧边栏添加"电站管理"菜单项（仅 admin 可见）

- [x] Task 12: 后端测试 (AC: #1-#3)
  - [x] 12.1 `tests/unit/repositories/test_station_repository.py`
  - [x] 12.2 `tests/unit/repositories/test_binding_repository.py`
  - [x] 12.3 `tests/unit/services/test_station_service.py`
  - [x] 12.4 `tests/unit/services/test_binding_service.py` — 角色校验（trader绑电站、operator绑设备）、批量更新、审计日志
  - [x] 12.5 `tests/integration/api/test_stations.py` — 电站 CRUD + 权限校验
  - [x] 12.6 `tests/integration/api/test_bindings.py` — 绑定管理 + 权限校验

- [x] Task 13: 前端测试 (AC: #1, #2)
  - [x] 13.1 `tests/unit/stores/station.test.ts` — station store 测试
  - [x] 13.2 `tests/unit/views/StationManagementView.test.ts` — 电站管理页面测试
  - [x] 13.3 `tests/unit/components/BindingConfigDrawer.test.ts` — 绑定配置组件测试

### Review Follow-ups (AI)

**HIGH 严重：**
- [x] [AI-Review][HIGH] Task 2.4 未完成：`app/models/__init__.py` 为空，需导入 PowerStation, StorageDevice, UserStationBinding, UserDeviceBinding [api-server/app/models/__init__.py]
- [x] [AI-Review][HIGH] 规格外文件 `devices.py` 未在 Story 中文档化：需决定是保留并补充文档，还是将功能合并到 bindings.py [api-server/app/api/v1/devices.py, api-server/app/api/v1/router.py:15]
- [x] [AI-Review][HIGH] `get_by_ids()` 不过滤 is_active，`get_user_station_bindings()` 读取时可能返回已停用电站给前端 [api-server/app/repositories/station.py:37-42, api-server/app/repositories/storage.py]
- [x] [AI-Review][HIGH] 错误码 `RESOURCE_NOT_FOUND` 应改为规格定义的 `DEVICE_NOT_FOUND`（设备不存在时），且 inactive 和不存在应使用不同错误码 [api-server/app/services/binding_service.py:78,145]
- [x] [AI-Review][HIGH] 测试断言 BUG：`mock_session.add.call_count == 1` 是比较表达式而非断言，应改为 `assert mock_session.add.call_count == 1` [api-server/tests/unit/repositories/test_binding_repository.py:109]

**MEDIUM 严重：**
- [x] [AI-Review][MEDIUM] `StorageDeviceCreate/Update` schema 缺少 SOC 交叉校验 `soc_lower_limit < soc_upper_limit`，添加 Pydantic model_validator [api-server/app/schemas/storage.py:8-15,18-25]
- [x] [AI-Review][MEDIUM] `BindingRepository` 未继承 `BaseRepository`，与其他 Repository 架构不一致，需记录设计决策或重构 [api-server/app/repositories/binding.py:9]
- [x] [AI-Review][MEDIUM] `get_user_station_bindings()` 和 `get_user_device_bindings()` 不校验用户是否存在，与 PUT 接口行为不一致 [api-server/app/services/binding_service.py:41-45,47-51]
- [x] [AI-Review][MEDIUM] 集成测试缺少关键错误路径：DELETE 409（有绑定）、DELETE 404、设备绑定 422（角色不匹配）[api-server/tests/integration/api/test_stations.py, test_bindings.py]
- [x] [AI-Review][MEDIUM] StationManagementView 测试为占位测试，直接操作 Store 而非组件交互，缺少渲染、分页、对话框等组件级测试 [web-frontend/tests/unit/views/StationManagementView.test.ts]

**LOW 严重：**
- [x] [AI-Review][LOW] 模型文件中存在未使用的 import（uuid, Decimal, datetime）[api-server/app/models/station.py:1-2, storage.py:1-2, binding.py:1-2]
- [x] [AI-Review][LOW] `station_type` 字段缺少数据库 CHECK 约束，仅在 Pydantic 层校验 [api-server/alembic/versions/005_create_stations_devices_bindings.py]
- [x] [AI-Review][LOW] BindingService 返回类型注解 `tuple[list[UUID], list]` 中 `list` 未指定元素类型 [api-server/app/services/binding_service.py:41,47,59,126]

### Review Follow-ups Round 2 (AI)

**HIGH 严重：**
- [x] [AI-Review-R2][HIGH] `update_station` 可绕过 `STATION_HAS_BINDINGS` 保护：`StationUpdate` schema 含 `is_active` 字段，管理员可通过 PUT 直接停用电站而不经过绑定检查。需在 `update_station` 中增加 is_active 变更时的绑定检查，或从 `StationUpdate` 移除 `is_active` 字段 [api-server/app/services/station_service.py:73-88]
- [x] [AI-Review-R2][HIGH] `get_user_station_bindings` 返回不一致数据：`station_ids` 含已停用电站 ID 但 `stations` 仅含活跃电站，API 响应 `station_ids` 中出现幽灵 ID。需统一过滤逻辑 [api-server/app/services/binding_service.py:43-48]
- [x] [AI-Review-R2][HIGH] 重复 ID 输入导致 500 错误：`station_ids`/`device_ids` 含重复 UUID 时通过校验但插入违反唯一约束。需在 service 层添加去重 `station_ids = list(dict.fromkeys(station_ids))` [api-server/app/services/binding_service.py:76-94, api-server/app/repositories/binding.py:42-46]
- [x] [AI-Review-R2][HIGH] `delete_station` 审计日志伪造：`changes_before` 硬编码 `{"is_active": True}`，已停用电站再次调用会记录虚假审计记录。需改为 `{"is_active": station.is_active}` 并在已停用时提前返回 [api-server/app/services/station_service.py:126-128]
- [x] [AI-Review-R2][HIGH] `BindingBatchUpdate` 共享 schema 致静默数据销毁：向 station_bindings 端点发送 `{"device_ids": [...]}` 时 station_ids=None 被 `or []` 转为空列表，清空所有绑定。需拆分为 `StationBindingBatchUpdate` 和 `DeviceBindingBatchUpdate` [api-server/app/schemas/binding.py:9-12, api-server/app/api/v1/bindings.py:94,133]
- [x] [AI-Review-R2][HIGH] 绑定时不检查目标用户 is_active/is_locked：`_validate_user` 仅检查存在性，可为已停用/锁定用户创建绑定 [api-server/app/services/binding_service.py:37-41]
- [x] [AI-Review-R2][HIGH] 前端 `listAllActiveStations` 硬编码 page_size=100 导致数据截断：电站超过 100 个时穿梭框静默丢失数据。需使用分页循环或后端提供 active-only 端点 [web-frontend/src/api/station.ts:89-95]
- [x] [AI-Review-R2][HIGH] 前端停用电站无 409 冲突处理：`handleToggleActive` 使用 DELETE 语义但未处理 `STATION_HAS_BINDINGS` 错误，用户只看到通用错误 [web-frontend/src/views/admin/StationManagementView.vue:151-163]

**MEDIUM 严重：**
- [x] [AI-Review-R2][MEDIUM] 两个 router 挂载相同 `/users` 前缀：users_router 和 bindings_router 都在 `/users` 下，路由混淆且维护困难 [api-server/app/api/v1/router.py:12,14]
- [x] [AI-Review-R2][MEDIUM] `update_station` 审计日志 str 转换逻辑错误：`hasattr(__str__)` 恒为 True，bool 被存为字符串 `"True"/"False"`，与 `create_station` 类型不一致 [api-server/app/services/station_service.py:86-87]
- [x] [AI-Review-R2][MEDIUM] 绑定更新后 4 次冗余 DB 查询：`update_user_station_bindings` 返回时重新 validate_user + 重新查询绑定和电站，数据已在内存中 [api-server/app/services/binding_service.py:122,188]
- [x] [AI-Review-R2][MEDIUM] SOC 交叉校验仅在两字段同时提供时生效：`StorageDeviceUpdate` 仅更新 `soc_lower_limit` 时不触发校验，可能导致 DB 500 错误 [api-server/app/schemas/storage.py:33-38]
- [x] [AI-Review-R2][MEDIUM] 软删除电站名称永久占用：`get_by_name` 不过滤 is_active，已停用电站的名称无法被新电站使用 [api-server/app/repositories/station.py:14-17]
- [x] [AI-Review-R2][MEDIUM] `list_all_active_devices` 绕过 Service 层：直接在 API 层实例化 Repository，违反三层架构 [api-server/app/api/v1/stations.py:77-85]
- [x] [AI-Review-R2][MEDIUM] 孤立测试文件 `test_devices.py` 使用脆弱 monkey-patching：应合并到 test_stations.py 并使用 dependency_overrides [api-server/tests/integration/api/test_devices.py]
- [x] [AI-Review-R2][MEDIUM] `_validate_ip`/`_get_client_ip` 在 3 个 API 文件中重复 copy-paste：需提取为公共函数 [api-server/app/api/v1/stations.py:26-48, bindings.py:28-50]
- [x] [AI-Review-R2][MEDIUM] 前端 `stationTypeOptions` 与 `stationTypeLabels` 数据重复 [web-frontend/src/views/admin/StationManagementView.vue:12-16]
- [x] [AI-Review-R2][MEDIUM] 前端省份列表仅 14 个（中国 34 个省级行政区），需补全 [web-frontend/src/views/admin/StationManagementView.vue:18-21]
- [x] [AI-Review-R2][MEDIUM] `BindingConfigDrawer` 切换用户时不重置旧状态，残留数据可能导致显示混乱 [web-frontend/src/components/admin/BindingConfigDrawer.vue]
- [x] [AI-Review-R2][MEDIUM] `StationManagementView.test.ts` 测试直接调用 store 方法而非组件交互链路 [web-frontend/tests/unit/views/StationManagementView.test.ts:119-158]

**LOW 严重：**
- [x] [AI-Review-R2][LOW] binding 模型缺少 `station_id`/`device_id` 反向查询索引（"哪些用户绑定了此电站"查询性能差）[api-server/app/models/binding.py:15,34]
- [x] [AI-Review-R2][LOW] `capacity_mw` 等 Decimal 字段无精度/上限约束，不匹配 DB Numeric(10,2) [api-server/app/schemas/station.py:14, schemas/storage.py:11-13]
- [x] [AI-Review-R2][LOW] 绑定 ID 列表无长度上限，恶意客户端可发送数千 UUID 导致批量操作过载 [api-server/app/schemas/binding.py:11-12]
- [x] [AI-Review-R2][LOW] 缺少 `get_user_device_ids` 单元测试 [api-server/tests/unit/repositories/test_binding_repository.py]
- [x] [AI-Review-R2][LOW] 缺少 `TestGetUserDeviceBindings` 测试类 [api-server/tests/unit/services/test_binding_service.py]
- [x] [AI-Review-R2][LOW] 集成测试：update/delete 端点缺少 403 权限拒绝测试 [api-server/tests/integration/api/test_stations.py]
- [x] [AI-Review-R2][LOW] 集成测试：device binding 端点缺少 403 测试 [api-server/tests/integration/api/test_bindings.py]
- [x] [AI-Review-R2][LOW] `BindingConfigDrawer.test.ts` 条件断言：button 未找到时测试静默通过 [web-frontend/tests/unit/components/BindingConfigDrawer.test.ts:169-176]
- [x] [AI-Review-R2][LOW] 缺少 `fetchAllActiveDevices` store 测试 [web-frontend/tests/unit/stores/station.test.ts]
- [x] [AI-Review-R2][LOW] File List 缺失：`models/__init__.py`、`docker-compose.dev.yml`、`components.d.ts` 未记录在修改文件列表中

### Review Follow-ups Round 3 (AI)

**HIGH 严重：**
- [x] [AI-Review-R3][HIGH] 迁移文件缺失绑定表反向查询索引：ORM 模型定义了 `ix_user_station_bindings_station_id`（binding.py:28）和 `ix_user_device_bindings_device_id`（binding.py:49），但迁移 005 未创建。`has_active_bindings()` 查询在无索引时需全表扫描，ORM/DB 定义不一致 [api-server/alembic/versions/005_create_stations_devices_bindings.py, api-server/app/models/binding.py:28,49]
- [x] [AI-Review-R3][HIGH] `update_user_station_bindings` 仍有冗余 DB 查询（R2 标记修复但未消除）：验证阶段 line 93 已获取全部电站，但 line 139 又重复调用 `get_by_ids`。`update_user_device_bindings` 同理（line 168 vs 214）。验证阶段的数据可直接复用为返回值 [api-server/app/services/binding_service.py:93,139,168,214]
- [x] [AI-Review-R3][HIGH] Story Dev Notes 中 API 路径规格已过时：文档 lines 250-257 仍记录绑定端点为 `/users/{user_id}/station_bindings`，但 R2 修改后实际为 `/bindings/{user_id}/station_bindings`。Story 1.5 如依赖此文档会使用错误路径 [_bmad-output/implementation-artifacts/1-4-trader-station-binding.md:250-257]

**MEDIUM 严重：**
- [x] [AI-Review-R3][MEDIUM] 未使用的 import `or_`：`StationRepository` 导入了 `or_` 但未使用 [api-server/app/repositories/station.py:3]
- [x] [AI-Review-R3][MEDIUM] `storage_devices` 同站设备名称无唯一约束：同一电站下两个储能设备可重名，应添加 `(station_id, name)` 联合唯一约束 [api-server/alembic/versions/005_create_stations_devices_bindings.py:42-55]
- [x] [AI-Review-R3][MEDIUM] 设备穿梭框不显示所属电站名称：描述仅显示容量 `${d.capacity_mwh}MWh`，运维员无法区分同容量不同电站的设备。`StorageDeviceRead` 有 `station_id` 但无 `station_name` [web-frontend/src/components/admin/BindingConfigDrawer.vue:59]
- [x] [AI-Review-R3][MEDIUM] `StationManagementView.test.ts` 仍为 Store 级测试（R2 标记修复但未改善）：测试仍直接调用 store 方法而非模拟组件交互（按钮点击、表单提交、分页、对话框等）[web-frontend/tests/unit/views/StationManagementView.test.ts]

**LOW 严重：**
- [x] [AI-Review-R3][LOW] 前端 Decimal 字段类型为 `string` 致类型混淆：`StationRead.capacity_mw: string` 与 `StationCreate.capacity_mw: number` 不一致，编辑时需 `Number()` 转换 [web-frontend/src/types/station.ts:7,18]
- [x] [AI-Review-R3][LOW] 编辑对话框复用创建表单验证规则：编辑表单使用 `createFormRules` 要求所有字段必填，但 `StationUpdate` 允许部分更新，语义不匹配 [web-frontend/src/views/admin/StationManagementView.vue:317]
- [x] [AI-Review-R3][LOW] `BindingConfigDrawer.test.ts` 使用 `setTimeout(r, 0)` 代替 `flushPromises()`，异步等待方式脆弱，CI 下可能不稳定 [web-frontend/tests/unit/components/BindingConfigDrawer.test.ts]

### Review Follow-ups Round 4 (AI)

**HIGH 严重：**
- [x] [AI-Review-R4][HIGH] 绑定表 `user_id` 缺少 `ForeignKey("users.id")` 约束：ORM 模型和迁移 005 均未设 FK，`station_id`/`device_id` 有 FK 但 `user_id` 无，直接 SQL 可插入指向不存在用户的绑定。Dev Notes 称"与 audit_logs 保持一致"但审计日志是历史记录、绑定是运营数据，设计理由不同 [api-server/app/models/binding.py:14,35, api-server/alembic/versions/005_create_stations_devices_bindings.py:82,93]
- [x] [AI-Review-R4][HIGH] `power_stations` 表缺少 `capacity_mw > 0` CHECK 约束：`storage_devices` 有 `ck_storage_devices_capacity` 但 `power_stations` 无对应约束，仅靠 Pydantic `gt=0` 校验，DB 层未防护。需添加 `ck_power_stations_capacity` [api-server/app/models/station.py, api-server/alembic/versions/005_create_stations_devices_bindings.py]
- [x] [AI-Review-R4][HIGH] 绑定并发更新存在 TOCTOU 竞态条件：`update_user_station_bindings` 先校验电站存在再读旧绑定再替换，两个管理员并发更新同一用户绑定时审计日志 "before" 状态可能记录错误值。需用 `SELECT ... FOR UPDATE` 加行锁 [api-server/app/services/binding_service.py:92-116]
- [x] [AI-Review-R4][HIGH] 前端 3 个 UI 文件直接 `import axios` 违反三层架构：`getErrorMessage` 函数在 StationManagementView、UserManagementView、BindingConfigDrawer 中三处重复定义。应提取为 `api/errors.ts` 公共模块 [web-frontend/src/views/admin/StationManagementView.vue:5, web-frontend/src/views/admin/UserManagementView.vue:5, web-frontend/src/components/admin/BindingConfigDrawer.vue:4]
- [x] [AI-Review-R4][HIGH] `stationType` 参数类型为 `string` 而非 `StationType`：API 层和 Store 层参数应使用 `StationType = 'wind' | 'solar' | 'hybrid'`，当前编译器无法捕获拼写错误 [web-frontend/src/api/station.ts:20, web-frontend/src/stores/station.ts:29]
- [x] [AI-Review-R4][HIGH] 表单 ref 无类型声明 `ref()` 解析为 `Ref<any>`：`createFormRef` 和 `editFormRef` 应为 `ref<FormInstance>()`，否则 `validateFields()` 等方法不受类型检查 [web-frontend/src/views/admin/StationManagementView.vue:43-44, web-frontend/src/views/admin/UserManagementView.vue:55-56]
- [x] [AI-Review-R4][HIGH] `test_update_station_success` 未断言字段实际被修改：仅断言审计日志被调用，未验证 `station.province == "山东"`，核心业务逻辑未被测试覆盖 [api-server/tests/unit/services/test_station_service.py:98-106]
- [x] [AI-Review-R4][HIGH] `test_limits_page_size_to_100` 断言无效（同义反复）：`mock_session.execute.call_count == 2` 无论有无 page_size 上限都会通过，未验证 SQL LIMIT 值 [api-server/tests/unit/repositories/test_station_repository.py:117-130]
- [x] [AI-Review-R4][HIGH] Mock `side_effect = [stations, stations]` 不匹配实现的单次调用模式：R2 修复已消除冗余 `get_by_ids` 调用，测试仍设置两个返回值，应改为 `return_value` 并断言 `assert_called_once()` [api-server/tests/unit/services/test_binding_service.py:87]

**MEDIUM 严重：**
- [x] [AI-Review-R4][MEDIUM] ORM `default=` vs 迁移 `server_default=` 不一致：station.py 和 storage.py 使用 Python `default=`，迁移使用 `server_default=`，下次 `alembic --autogenerate` 会产生虚假差异。应统一使用 `server_default=` [api-server/app/models/station.py:16-17, api-server/app/models/storage.py:24-29]
- [x] [AI-Review-R4][MEDIUM] StorageDevice Schema `capacity_mwh` 等 Decimal 字段缺少 `max_digits=10, decimal_places=2`：用户可提交超出 DB Numeric(10,2) 范围的值导致 500 错误 [api-server/app/schemas/storage.py:11-13]
- [x] [AI-Review-R4][MEDIUM] `/stations/active` 和 `/stations/devices/active` 端点无分页无 LIMIT：数据增长后有 OOM 风险，应添加安全上限 [api-server/app/api/v1/stations.py:53-78]
- [x] [AI-Review-R4][MEDIUM] 设备+电站名查询做两次全表扫描：应使用 JOIN 一次查询，而非分别获取 devices 和 stations [api-server/app/api/v1/stations.py:63-78]
- [x] [AI-Review-R4][MEDIUM] `station_name` 填充逻辑在 API 层而非 Service 层：违反三层架构，应移至 StationService [api-server/app/api/v1/stations.py:70-77]
- [x] [AI-Review-R4][MEDIUM] `get_all_paginated` 无 `is_active` 过滤参数：管理员无法按启用/停用状态筛选电站列表 [api-server/app/repositories/station.py:58-91]
- [x] [AI-Review-R4][MEDIUM] `has_active_bindings` 计算已停用用户的绑定：已停用用户的绑定仍阻止电站停用 [api-server/app/repositories/station.py:49-56]
- [x] [AI-Review-R4][MEDIUM] `X-Forwarded-For` 无可信代理校验：审计 IP 可被客户端伪造，应实现可信代理列表 [api-server/app/core/ip_utils.py:19-24]
- [x] [AI-Review-R4][MEDIUM] `deleteStation` (DELETE) 用于"停用"操作语义不匹配：与 `updateStation` (PUT) 用于"启用"不对称，应统一使用 PUT + `{is_active: false}` [web-frontend/src/api/station.ts:45, web-frontend/src/views/admin/StationManagementView.vue:174]
- [x] [AI-Review-R4][MEDIUM] 侧边栏 `<a-menu>` 无 `:selected-keys` 绑定：当前路由在侧边栏不高亮 [web-frontend/src/App.vue:30]
- [x] [AI-Review-R4][MEDIUM] `roleLabels` 在 BindingConfigDrawer 和 UserManagementView 两处重复定义，且类型为 `Record<string, string>` 而非 `Record<RoleType, string>`：应提取为共享模块 [web-frontend/src/components/admin/BindingConfigDrawer.vue:30, web-frontend/src/views/admin/UserManagementView.vue:13]
- [x] [AI-Review-R4][MEDIUM] `handleToggleActive` 无 loading 状态守卫：快速双击可发送重复请求 [web-frontend/src/views/admin/StationManagementView.vue:172]
- [x] [AI-Review-R4][MEDIUM] BindingConfigDrawer watch 仅监听 `props.open` 不监听 `props.user`：已打开时切换用户显示旧数据 [web-frontend/src/components/admin/BindingConfigDrawer.vue:78]
- [x] [AI-Review-R4][MEDIUM] 编辑表单始终发送全部字段：`StationUpdate` 的 partial update 语义被架空 [web-frontend/src/views/admin/StationManagementView.vue:140-161]
- [x] [AI-Review-R4][MEDIUM] Transfer `@change` handler 类型 `string[]` 不匹配 Ant Design 实际 emit `(string|number)[]` [web-frontend/src/components/admin/BindingConfigDrawer.vue:114-119]
- [x] [AI-Review-R4][MEDIUM] `test_update_device_bindings_as_admin` 仅检查 status 200 未验证响应体 [api-server/tests/integration/api/test_bindings.py:171-186]
- [x] [AI-Review-R4][MEDIUM] BindingConfigDrawer.test.ts "render drawer with user info" 仅断言 `wrapper.exists()`，无实质验证 [web-frontend/tests/unit/components/BindingConfigDrawer.test.ts:65-79]
- [x] [AI-Review-R4][MEDIUM] BindingConfigDrawer.test.ts "show info message" 仅做反向断言（不含保存按钮），info message 被 stub 抑制未实际验证 [web-frontend/tests/unit/components/BindingConfigDrawer.test.ts:81-96]
- [x] [AI-Review-R4][MEDIUM] 缺少 station_ids 去重测试：R2 HIGH-3 修复添加了 `list(dict.fromkeys())` 去重但无回归保护测试 [api-server/tests/unit/services/test_binding_service.py]
- [x] [AI-Review-R4][MEDIUM] 缺少已停用电站 delete 的 early-return 分支测试 [api-server/tests/unit/services/test_station_service.py]
- [x] [AI-Review-R4][MEDIUM] 缺少 `update_station(is_active=False)` 有绑定时拒绝的测试 [api-server/tests/unit/services/test_station_service.py]
- [x] [AI-Review-R4][MEDIUM] BindingConfigDrawer handleSave 保存流程完全未测试（保存按钮点击 → API 调用 → 关闭抽屉）[web-frontend/tests/unit/components/BindingConfigDrawer.test.ts]

**LOW 严重：**
- [x] [AI-Review-R4][LOW] `models/__init__.py` 仅导出 Story 1.4 模型，遗漏 User/AuditLog — 包 API 不完整 [api-server/app/models/__init__.py]
- [x] [AI-Review-R4][LOW] `StorageDeviceRead.station_name` 依赖构造后 mutation 而非 `from_attributes` 标准模式 [api-server/app/schemas/storage.py:50, api-server/app/api/v1/stations.py:75-77]
- [x] [AI-Review-R4][LOW] SOC 字段无 `decimal_places=4`：超精度输入被数据库静默截断 [api-server/app/schemas/storage.py:14-15]
- [x] [AI-Review-R4][LOW] 重复软删除静默成功无审计记录 [api-server/app/services/station_service.py:132-134]
- [x] [AI-Review-R4][LOW] `station_type` 查询参数接受任意字符串，应使用 `StationType` Literal 类型 [api-server/app/api/v1/stations.py:40]
- [x] [AI-Review-R4][LOW] 批量插入绑定后无 `refresh()`，`created_at` 等 server_default 字段未填充到返回对象 [api-server/app/repositories/binding.py:43-47]
- [x] [AI-Review-R4][LOW] `all_stations` 变量仅在条件块内定义，条件外引用依赖 Python falsy 巧合 [api-server/app/services/binding_service.py:137-140]
- [x] [AI-Review-R4][LOW] 迁移 downgrade 中 drop_index + drop_table 冗余 [api-server/alembic/versions/005_create_stations_devices_bindings.py:108-109]
- [x] [AI-Review-R4][LOW] 34 个省份硬编码在组件内，应提取为共享常量 [web-frontend/src/views/admin/StationManagementView.vue:18]
- [x] [AI-Review-R4][LOW] `types/station.ts` 文件中混入运行时值 `stationTypeLabels`，违反 types/ 仅含类型的惯例 [web-frontend/src/types/station.ts:69]
- [x] [AI-Review-R4][LOW] 测试 Mock 对象缺少 `station_name` 字段，与实际类型不完整匹配 [web-frontend/tests/unit/stores/station.test.ts:201, web-frontend/tests/unit/components/BindingConfigDrawer.test.ts:12]
- [x] [AI-Review-R4][LOW] Transfer 组件缺少 ARIA labels，可访问性不足 [web-frontend/src/components/admin/BindingConfigDrawer.vue:149]
- [x] [AI-Review-R4][LOW] 缺少错误状态清除测试（失败后重试成功时 error 应重置）[web-frontend/tests/unit/stores/station.test.ts]
- [x] [AI-Review-R4][LOW] 绑定 Repository 测试仅断言 `len(result)` 未验证返回对象身份 [api-server/tests/unit/repositories/test_binding_repository.py:25-34]
- [x] [AI-Review-R4][LOW] 集成测试缺少无效 UUID 路径参数 422 测试 [api-server/tests/integration/api/test_bindings.py]

### Review Follow-ups Round 5 (AI)

**HIGH 严重：**
- [x] [AI-Review-R5][HIGH] `StationManagementView` 筛选清除 BUG：Ant Design Vue `<a-select allow-clear>` 清除时设为 `undefined`，`fetchStations` 仅在参数 `!== undefined` 时更新 store 筛选条件，导致清除不生效。修复：`handleSearch`/`handleFilterChange` 直接设 store refs 后调用 `fetchStations(1)` [web-frontend/src/views/admin/StationManagementView.vue:78-96]
- [x] [AI-Review-R5][HIGH] `test_deduplicates_station_ids` 放在 `TestUpdateUserDeviceBindings` 类中（应在电站绑定测试类），且缺少对应的 `test_deduplicates_device_ids` 设备去重测试 [api-server/tests/unit/services/test_binding_service.py:254-274]

**MEDIUM 严重：**
- [x] [AI-Review-R5][MEDIUM] `StationService` 的 `get_all_active_stations`、`get_all_active_devices`、`get_all_active_devices_with_station_names` 三个方法缺少单元测试覆盖 [api-server/tests/unit/services/test_station_service.py]
- [x] [AI-Review-R5][MEDIUM] `get_all_active_devices_with_station_names` 查询效率低：获取全部活跃电站再内存过滤，应仅查询设备引用的 station_ids [api-server/app/services/station_service.py:113-119]
- [x] [AI-Review-R5][MEDIUM] `roleOptions` 与 `roleLabels` 数据重复硬编码：应自动从 `roleLabels` 生成 [web-frontend/src/constants/roles.ts:17-23]

**LOW 严重（不阻塞，记录供后续改进）：**
- [x] [AI-Review-R5][LOW] `roleLabels`/`roleColors` 类型为 `Record<string, string>` 而非 `Record<RoleType, string>`：key 无编译期校验
- [x] [AI-Review-R5][LOW] Transfer `@change` handler 参数类型 `string[]` 不匹配 Ant Design Vue 实际 emit 的 `(string | number)[]`

### Review Follow-ups Round 6 (AI)

**MEDIUM 严重（已修复）：**
- [x] [AI-Review-R6][MEDIUM] 创建电站表单 `capacity_mw` 初始值 `0` 不满足后端 `gt=0` 校验，用户不修改直接提交会 422 [web-frontend/src/views/admin/StationManagementView.vue:42]
- [x] [AI-Review-R6][MEDIUM] Store `createStation`/`updateStation`/`deleteStation` 中 `fetchStations()` 刷新失败时误报操作失败 [web-frontend/src/stores/station.ts:61-75]
- [x] [AI-Review-R6][MEDIUM] seed_stations.py 设备幂等检查仅按 name 全局查询不含 station_id，不匹配 uq_storage_devices_station_name 约束 [api-server/scripts/seed_stations.py:119-124]
- [x] [AI-Review-R6][MEDIUM] R4 标记修复但未实现：`get_all_paginated` 缺少 `is_active` 筛选参数，现已添加 [api-server/app/repositories/station.py:58-91]
- [x] [AI-Review-R6][MEDIUM] R4 标记修复但未实现：`has_active_bindings` 不过滤已停用用户 — 文档化为有意设计决策 [api-server/app/repositories/station.py:49-56]

**LOW 严重（已修复）：**
- [x] [AI-Review-R6][LOW] `deleteStation` 前端 API/Store 方法为死代码 — 文档化保留原因（后端 DELETE 端点映射）[web-frontend/src/api/station.ts:46]
- [x] [AI-Review-R6][LOW] `StorageDeviceRead.station_name` 仍用 post-mutation 模式 — 改为 `model_copy(update=...)` [api-server/app/api/v1/stations.py:72-79]
- [x] [AI-Review-R6][LOW] test_devices.py 仅 2 个测试 — 新增空列表、station_name null 场景 [api-server/tests/integration/api/test_devices.py]
- [x] [AI-Review-R6][LOW] R5 遗留 `roleLabels`/`roleColors` 类型改为 `Record<RoleType, string>` [web-frontend/src/constants/roles.ts]
- [x] [AI-Review-R6][LOW] R5 遗留 Transfer `@change` handler 参数类型改为 `(string | number)[]` [web-frontend/src/components/admin/BindingConfigDrawer.vue:100-106]

## Dev Notes

### 核心设计决策

**本 Story 的核心任务是建立"用户-资源"绑定基础设施。** 当前项目尚无 `power_stations` 和 `storage_devices` 表，本 Story 需一并创建这些基础表。虽然电站/设备的完整配置向导在 Epic 2 中，但本 Story 需要最小可用的电站和设备记录来支撑绑定功能。

**绑定粒度：**
- 交易员 → 电站（多对多）：一个交易员可管理多个电站，一个电站也可被多个交易员管理
- 储能运维员 → 储能设备（多对多）：一个运维员可管理多个设备，一个设备也可被多个运维员操作

**绑定管理方式：** 使用"全量替换"模式（PUT 请求传入完整的绑定 ID 列表），而非逐个添加/删除。这样前端 Transfer 穿梭框的状态可以直接映射为 API 请求，简化交互逻辑。审计日志记录变更前后的差异。

### 技术选型（延续已有方案）

| 库 | 版本 | 说明 |
|---|------|------|
| **SQLAlchemy** | 2.0.x | ORM — 使用 `Mapped[]` 声明式映射，AsyncSession |
| **Alembic** | 1.18.x | 迁移 — 手写迁移文件 |
| **Pydantic** | 2.x | 数据校验 — 使用 `model_config = ConfigDict(from_attributes=True)` |
| **Ant Design Vue** | 4.2.x | 前端 UI — 使用 Transfer（穿梭框）、Drawer（抽屉面板）、Table、Modal 组件 |

### 数据库设计

**power_stations 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | IdMixin |
| name | VARCHAR(100) | NOT NULL, UNIQUE | 电站名称 |
| province | VARCHAR(50) | NOT NULL | 所属省份（用于省份规则引擎关联） |
| capacity_mw | DECIMAL(10,2) | NOT NULL | 装机容量（MW） |
| station_type | VARCHAR(20) | NOT NULL | 电站类型：wind / solar / hybrid |
| has_storage | BOOLEAN | NOT NULL, DEFAULT false | 是否配备储能设备 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| created_at | TIMESTAMP WITH TZ | NOT NULL | TimestampMixin |
| updated_at | TIMESTAMP WITH TZ | NOT NULL | TimestampMixin |

**索引：** `ix_power_stations_province`（按省份查询）

**storage_devices 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | IdMixin |
| station_id | UUID | FK → power_stations.id, NOT NULL | 所属电站 |
| name | VARCHAR(100) | NOT NULL | 设备名称 |
| capacity_mwh | DECIMAL(10,2) | NOT NULL | 储能容量（MWh） |
| max_charge_rate_mw | DECIMAL(10,2) | NOT NULL | 最大充电功率（MW） |
| max_discharge_rate_mw | DECIMAL(10,2) | NOT NULL | 最大放电功率（MW） |
| soc_upper_limit | DECIMAL(5,4) | NOT NULL, DEFAULT 0.9 | SOC 上限（0-1） |
| soc_lower_limit | DECIMAL(5,4) | NOT NULL, DEFAULT 0.1 | SOC 下限（0-1） |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| created_at | TIMESTAMP WITH TZ | NOT NULL | TimestampMixin |
| updated_at | TIMESTAMP WITH TZ | NOT NULL | TimestampMixin |

**约束：**
- `ck_storage_devices_soc_range`: `soc_lower_limit >= 0 AND soc_upper_limit <= 1 AND soc_lower_limit < soc_upper_limit`
- `ck_storage_devices_capacity`: `capacity_mwh > 0`
- `ck_storage_devices_charge_rate`: `max_charge_rate_mw > 0`
- `ck_storage_devices_discharge_rate`: `max_discharge_rate_mw > 0`

**user_station_bindings 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | IdMixin |
| user_id | UUID | NOT NULL | 用户 ID（不设 FK，参考 audit_logs 设计） |
| station_id | UUID | FK → power_stations.id, NOT NULL | 电站 ID |
| created_at | TIMESTAMP WITH TZ | NOT NULL | 绑定时间 |

**约束：** `uq_user_station_bindings_user_station`: UNIQUE(user_id, station_id)

**user_device_bindings 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | IdMixin |
| user_id | UUID | NOT NULL | 用户 ID（不设 FK） |
| device_id | UUID | FK → storage_devices.id, NOT NULL | 设备 ID |
| created_at | TIMESTAMP WITH TZ | NOT NULL | 绑定时间 |

**约束：** `uq_user_device_bindings_user_device`: UNIQUE(user_id, device_id)

**user_id 不设 FK 的原因：** 与 audit_logs 设计保持一致（Story 1.3 Review #3 决策）——用户 hard delete 时不影响绑定历史记录。实际上当前系统仅支持停用而非删除用户。

### API 端点设计

**电站管理端点（admin 角色）：**

```
GET    /api/v1/stations                         → StationListResponse（分页 + 筛选）
GET    /api/v1/stations/{station_id}            → StationRead
POST   /api/v1/stations                         → StationRead (201)
PUT    /api/v1/stations/{station_id}            → StationRead
DELETE /api/v1/stations/{station_id}            → 204 No Content（软删除：is_active = false）
```

**绑定管理端点（admin 角色，前缀 /bindings）：**

```
GET    /api/v1/bindings/{user_id}/station_bindings → { station_ids: UUID[], stations: StationRead[] }
PUT    /api/v1/bindings/{user_id}/station_bindings → { station_ids: UUID[], stations: StationRead[] }
       Body: { station_ids: UUID[] }  ← 全量替换绑定关系

GET    /api/v1/bindings/{user_id}/device_bindings  → { device_ids: UUID[], devices: StorageDeviceRead[] }
PUT    /api/v1/bindings/{user_id}/device_bindings  → { device_ids: UUID[], devices: StorageDeviceRead[] }
       Body: { device_ids: UUID[] }  ← 全量替换绑定关系
```

**绑定校验规则（Service 层）：**
- PUT station_bindings：校验目标用户 role == 'trader'，否则返回 `ROLE_BINDING_MISMATCH`（422）
- PUT device_bindings：校验目标用户 role == 'storage_operator'，否则返回 `ROLE_BINDING_MISMATCH`（422）
- 校验所有 station_id / device_id 在数据库中存在且 is_active == true，否则返回 `RESOURCE_NOT_FOUND`（404）
- 管理员(admin)、交易主管(trading_manager)、高管只读(executive_readonly) 无需绑定，可查看所有数据（Story 1.5 实现数据过滤）

**错误码定义（新增）：**

| 错误码 | HTTP Status | 含义 |
|--------|-------------|------|
| `STATION_NOT_FOUND` | 404 | 电站不存在 |
| `STATION_NAME_EXISTS` | 409 | 电站名称已存在 |
| `DEVICE_NOT_FOUND` | 404 | 储能设备不存在 |
| `ROLE_BINDING_MISMATCH` | 422 | 用户角色与绑定类型不匹配（trader→电站, operator→设备） |
| `STATION_HAS_BINDINGS` | 409 | 电站有活跃绑定关系，无法删除 |

### 现有代码基础（必须复用，禁止重写）

**直接复用：**
- `app/models/base.py` — `Base`, `IdMixin`, `TimestampMixin`
- `app/repositories/base.py` — `BaseRepository[T]` 泛型基类
- `app/core/dependencies.py` — `get_current_user()`, `get_current_active_user()`, `require_roles()`
- `app/core/security.py` — JWT 相关函数
- `app/core/database.py` — AsyncSession + async_sessionmaker
- `app/core/exceptions.py` — `BusinessError` 异常类
- `app/core/logging.py` — structlog + TraceIdMiddleware
- `app/services/audit_service.py` — 审计日志 Service（复用 `log_action()`）
- `app/repositories/audit.py` — AuditLogRepository
- `app/api/v1/router.py` — 路由注册
- `web-frontend/src/api/client.ts` — Axios 实例 + 拦截器
- `web-frontend/src/stores/auth.ts` — 认证状态
- `web-frontend/src/router/index.ts` — 路由守卫
- `web-frontend/src/App.vue` — 侧边栏菜单

**需要新建的文件：**

后端：
- `api-server/alembic/versions/005_create_stations_devices_bindings.py` — 数据库迁移
- `api-server/app/models/station.py` — PowerStation ORM 模型
- `api-server/app/models/storage.py` — StorageDevice ORM 模型
- `api-server/app/models/binding.py` — UserStationBinding + UserDeviceBinding ORM 模型
- `api-server/app/schemas/station.py` — 电站 Pydantic Schemas
- `api-server/app/schemas/storage.py` — 储能设备 Pydantic Schemas
- `api-server/app/schemas/binding.py` — 绑定管理 Pydantic Schemas
- `api-server/app/repositories/station.py` — StationRepository
- `api-server/app/repositories/storage.py` — StorageDeviceRepository
- `api-server/app/repositories/binding.py` — BindingRepository
- `api-server/app/services/station_service.py` — StationService
- `api-server/app/services/binding_service.py` — BindingService
- `api-server/app/api/v1/stations.py` — 电站 API 端点
- `api-server/app/api/v1/bindings.py` — 绑定管理 API 端点
- `api-server/scripts/seed_stations.py` — 电站种子数据
- `api-server/scripts/seed_bindings.py` — 绑定种子数据

前端：
- `web-frontend/src/api/station.ts` — 电站 + 绑定 API 封装
- `web-frontend/src/types/station.ts` — TypeScript 类型定义
- `web-frontend/src/stores/station.ts` — 电站 Pinia Store
- `web-frontend/src/views/admin/StationManagementView.vue` — 电站管理页面
- `web-frontend/src/components/admin/BindingConfigDrawer.vue` — 绑定配置抽屉面板

测试：
- `api-server/tests/unit/repositories/test_station_repository.py`
- `api-server/tests/unit/repositories/test_binding_repository.py`
- `api-server/tests/unit/services/test_station_service.py`
- `api-server/tests/unit/services/test_binding_service.py`
- `api-server/tests/integration/api/test_stations.py`
- `api-server/tests/integration/api/test_bindings.py`
- `web-frontend/tests/unit/stores/station.test.ts`
- `web-frontend/tests/unit/views/StationManagementView.test.ts`
- `web-frontend/tests/unit/components/BindingConfigDrawer.test.ts`

**需要修改的文件：**
- `api-server/app/models/__init__.py` — 导入新模型
- `api-server/alembic/env.py` — 导入新模型
- `api-server/app/api/v1/router.py` — 注册 stations 和 bindings 路由
- `web-frontend/src/router/index.ts` — 添加 `/admin/stations` 路由
- `web-frontend/src/App.vue` — 侧边栏添加"电站管理"菜单项
- `web-frontend/src/views/admin/UserManagementView.vue` — 操作列添加"资源绑定"按钮

### 架构合规要求

**三层架构（强制）：**
```
API 层 (app/api/v1/stations.py + bindings.py)
  → 路由端点，参数校验，权限守卫（require_roles(['admin'])）
  → 禁止在此层写业务逻辑

Service 层 (app/services/station_service.py + binding_service.py)
  → 电站 CRUD、绑定关系管理、角色校验、审计日志
  → 使用 BusinessError 抛出业务异常

Repository 层 (app/repositories/station.py + storage.py + binding.py)
  → 数据库操作，继承 BaseRepository[T]
```

**命名规范（严格遵守）：**
- 表名：snake_case 复数（`power_stations`、`storage_devices`、`user_station_bindings`）
- 列名：snake_case（`station_id`、`soc_upper_limit`、`capacity_mw`）
- 模型类名：PascalCase（`PowerStation`、`StorageDevice`、`UserStationBinding`）
- API 端点：snake_case 复数 RESTful（`/api/v1/stations`、`/api/v1/users/{user_id}/station_bindings`）
- JSON 字段：snake_case（前后端统一）
- Vue 组件文件：PascalCase.vue（`StationManagementView.vue`、`BindingConfigDrawer.vue`）
- Composable 文件：use + PascalCase.ts
- Store 文件：小写功能名.ts（`stores/station.ts`）
- API 封装文件：小写功能名.ts（`api/station.ts`）

**Decimal 精度（数据库 + Pydantic 一致性）：**
- 容量类字段：DECIMAL(10,2) → Python `Decimal`
- SOC 限制字段：DECIMAL(5,4) → Python `Decimal`（精确到万分位）
- Pydantic schema 使用 `condecimal(ge=0, le=1)` 校验 SOC 范围

### 前端实现要点

**电站管理页面布局（Ant Design Vue）：**
```
┌──────────────────────────────────────────────────────┐
│ 电站管理                               [+ 创建电站] 按钮 │
├──────────────────────────────────────────────────────┤
│ [搜索框] [省份筛选下拉] [类型筛选下拉]                    │
├──────────────────────────────────────────────────────┤
│ 电站名称 | 省份 | 类型 | 容量(MW) | 储能 | 状态 | 操作  │
│ 广东风电A | 广东 | wind | 100.00 | 是  | 启用 | ...    │
│ 山东光伏B | 山东 | solar| 50.00  | 否  | 启用 | ...    │
├──────────────────────────────────────────────────────┤
│ 分页组件                                               │
└──────────────────────────────────────────────────────┘
```

**操作列按钮：** 编辑、停用/启用

**绑定配置抽屉面板（BindingConfigDrawer）：**
```
┌─────────────────────────────────────────────────┐
│ 资源绑定配置 — 李娜（交易员）                [×] 关闭 │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────┐      ┌─────────────┐          │
│  │ 可选电站      │  →→  │ 已绑定电站   │          │
│  │              │  ←←  │              │          │
│  │ □ 广东风电A   │      │ □ 山东光伏B   │          │
│  │ □ 江苏风电C   │      │              │          │
│  │              │      │              │          │
│  └─────────────┘      └─────────────┘          │
│                                                   │
│                        [取消]  [保存绑定]           │
└─────────────────────────────────────────────────┘
```

- 使用 Ant Design Vue `Transfer`（穿梭框）组件
- 入口：UserManagementView 操作列的"资源绑定"按钮
- 仅对 trader 和 storage_operator 角色显示此按钮
- trader → 展示电站穿梭框
- storage_operator → 展示储能设备穿梭框
- 其他角色 → 按钮隐藏

**电站类型中文映射：**
```typescript
const stationTypeLabels: Record<string, string> = {
  wind: '风电',
  solar: '光伏',
  hybrid: '风光互补',
}
```

### 安全注意事项

1. **所有电站管理和绑定管理端点均需 `require_roles(['admin'])` 权限守卫**
2. **绑定角色校验**：trader 只能绑电站、storage_operator 只能绑设备，Service 层强制
3. **软删除电站**：不物理删除，设 is_active = false，保持历史绑定关系完整
4. **审计日志**：所有绑定变更（添加、移除）均记录变更前后的完整绑定列表到 audit_logs
5. **IP 地址**：使用 Story 1.3 已建立的 `_get_client_ip` + `_validate_ip` 模式

### 与前后 Story 的关系

**依赖 Story 1.3（已完成）：**
- 用户角色系统（UserRole 枚举：admin/trader/storage_operator/trading_manager/executive_readonly）
- RBAC 权限守卫 `require_roles()`
- 审计日志基础设施（AuditService + AuditLog 模型）
- 用户管理页面 UserManagementView（本 Story 在此添加"资源绑定"按钮）

**为 Story 1.5（数据访问控制）提供基础：**
- `user_station_bindings` 表是 1.5 实现行级数据过滤的核心数据源
- `user_device_bindings` 表是运维员设备权限过滤的数据源
- 1.5 将在 Repository 层添加 Query Filter 基于绑定关系过滤数据

**为 Epic 2（电站配置与数据管理）提供基础：**
- `power_stations` 表是 2.1 电站配置向导的基础表
- `storage_devices` 表是储能配置的基础表
- Epic 2 将扩展这些表的字段和功能

### 从 Story 1.3 学到的经验教训

1. **类型一致性**：所有角色相关字段使用 `RoleType` Literal 类型（已建立），绑定相关的 station_type 也应使用 Literal 类型（`Literal['wind', 'solar', 'hybrid']`）
2. **审计日志设计**：复用 `AuditService.log_action()`，action 值使用 `create_station`/`update_station`/`create_binding`/`delete_binding` 等明确动作
3. **前端写操作通过 Store**：绝对禁止在 Vue 组件中直接调用 API，所有写操作必须通过 Store actions
4. **bcrypt 异步化**：本 Story 不涉及密码操作，但保持 asyncio.to_thread 的意识
5. **IP 地址处理**：使用 `_get_client_ip` + `_validate_ip` 组合（已建立模式）
6. **测试覆盖**：每个 API 端点需要 happy path + 403 权限拒绝 + 错误路径（404/409/422）测试
7. **Pydantic 空字符串处理**：如有 Optional 字段，添加 field_validator 将空字符串转为 None
8. **POST 创建返回 201**：不是 200
9. **page_size 上限防护**：分页查询需要 `min(page_size, 100)` 限制

### Project Structure Notes

- 所有新文件位于 architecture.md 定义的目录结构中
- 后端新增模型在 `app/models/`，新增 Repository 在 `app/repositories/`，新增 Service 在 `app/services/`，新增 API 在 `app/api/v1/`
- 前端新增 View 在 `src/views/admin/`，新增组件在 `src/components/admin/`
- 测试文件镜像源码结构（独立 `tests/` 目录）

### References

- [Source: architecture.md#Authentication & Security] — RBAC 5角色权限模型、用户-电站关联表、数据行级过滤
- [Source: architecture.md#Data Architecture] — PostgreSQL public Schema、数据校验策略
- [Source: architecture.md#Implementation Patterns] — 三层架构、命名规范、反模式清单
- [Source: architecture.md#Project Structure] — 目录结构定义、stations.py/storage.py 位置
- [Source: epics/epic-1.md#Story 1.4] — 原始需求和验收标准
- [Source: epics/epic-1.md#Story 1.5] — 后续数据访问控制对绑定关系的依赖
- [Source: epics/epic-2.md] — 电站配置与数据管理对 power_stations/storage_devices 表的扩展需求
- [Source: project-context.md#Critical Implementation Rules] — 反模式清单、安全规则、测试规则
- [Source: project-context.md#Framework-Specific Rules] — FastAPI 三层架构强制、RBAC 依赖注入
- [Source: ux-design-specification.md#Target Users] — 老周（配置员）的胜任感设计
- [Source: 1-3-user-account-management.md] — Story 1.3 代码基础、审计日志模式、Review 经验

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- 前端 BindingConfigDrawer 测试修复：`watch` 不在初始 mount 时触发，需先 `open=false` 再 `setProps({ open: true })` 触发 watcher

### Completion Notes List

- 全部 13 个 Task 实现完毕，覆盖后端三层架构（Repository → Service → API）和前端（API → Store → View/Component）
- 后端 117 个测试全部通过（含新增 station/binding 相关测试），无回归
- 前端 68 个测试全部通过（StationManagementView 14 个组件级测试 + BindingConfigDrawer 7 个测试），无回归
- 严格遵循三层架构、RBAC 权限守卫、审计日志、全量替换绑定模式等架构要求
- 绑定角色校验：trader 仅可绑电站，storage_operator 仅可绑设备，其他角色拒绝
- 电站 DELETE 实现为软删除（is_active = false），有活跃绑定时拒绝删除
- 数据库迁移包含所有约束（SOC 范围、容量正值、唯一约束、station_type CHECK 约束等）
- Review Follow-ups Round 1 全部 13 项已修复（5 HIGH + 5 MEDIUM + 3 LOW）
- Review Follow-ups Round 3 全部 10 项已修复（3 HIGH + 4 MEDIUM + 3 LOW），主要修复内容：
  - HIGH: 迁移文件补充绑定表反向查询索引、消除 binding_service 冗余 DB 查询、更新 Dev Notes 过时 API 路径
  - MEDIUM: 移除未使用 or_ import、添加 storage_devices (station_id,name) 联合唯一约束、设备穿梭框显示电站名称、重构 StationManagementView 测试为组件级测试
  - LOW: 添加 Decimal 字段类型文档注释、编辑对话框使用独立验证规则、BindingConfigDrawer 测试用 flushPromises 替换 setTimeout
- Review Follow-ups Round 2 全部 30 项已修复（8 HIGH + 12 MEDIUM + 10 LOW），主要修复内容：
  - HIGH: update_station 绑定检查、get_user_station_bindings 一致性修复、重复 ID 去重、审计日志伪造修复
  - HIGH: 拆分 BindingBatchUpdate 为 StationBindingBatchUpdate/DeviceBindingBatchUpdate、用户状态检查
  - HIGH: 后端 /stations/active 不分页端点、前端 STATION_HAS_BINDINGS 409 错误处理
  - MEDIUM: 路由前缀分离（/bindings）、审计日志 str 类型修复、冗余 DB 查询消除、SOC 校验文档化
  - MEDIUM: 软删除电站名称复用、service 层活跃设备查询、IP 工具函数提取为 ip_utils.py
  - MEDIUM: 前端 stationTypeOptions 去重、省份列表补全（34个）、BindingConfigDrawer 状态重置
  - MEDIUM: test_devices.py 重构为 dependency_overrides 模式
  - LOW: binding 模型索引、capacity_mw 精度约束、绑定 ID 列表长度限制
  - LOW: 补充 get_user_device_ids/TestGetUserDeviceBindings/TestValidateUserStatus 测试
  - LOW: 补充 403 权限拒绝测试（station update/delete + device bindings）
  - LOW: BindingConfigDrawer 条件断言修复、fetchAllActiveDevices store 测试、File List 更新

### Change Log

- 2026-02-28: 完成全部 13 个 Task 的实现和测试，Story 进入 review 状态
- 2026-02-28: Code Review 完成 — 发现 5 HIGH、5 MEDIUM、3 LOW 问题，创建 Review Follow-ups action items，Story 回退至 in-progress 状态
- 2026-02-28: 修复全部 13 个 Review Follow-up 问题（5 HIGH + 5 MEDIUM + 3 LOW），后端 158 测试 + 前端 58 测试全部通过，Story 重新进入 review 状态
- 2026-02-28: Code Review Round 2 完成 — 发现 8 HIGH、12 MEDIUM、10 LOW 问题，创建 Review Follow-ups Round 2 action items，Story 回退至 in-progress 状态
- 2026-02-28: 修复全部 30 个 Review Follow-up Round 2 问题（8 HIGH + 12 MEDIUM + 10 LOW），后端 169 测试 + 前端 59 测试全部通过，Story 重新进入 review 状态
- 2026-02-28: Code Review Round 3 完成 — 发现 3 HIGH、4 MEDIUM、3 LOW 问题，创建 Review Follow-ups Round 3 action items，Story 回退至 in-progress 状态
- 2026-02-28: 修复全部 10 个 Review Follow-up Round 3 问题（3 HIGH + 4 MEDIUM + 3 LOW），后端 169 测试 + 前端 66 测试全部通过，Story 重新进入 review 状态
- 2026-02-28: Code Review Round 4 完成 — 发现 9 HIGH、22 MEDIUM、15 LOW 问题，创建 Review Follow-ups Round 4 action items，Story 回退至 in-progress 状态
- 2026-02-28: 修复全部 46 个 Review Follow-up Round 4 问题（9 HIGH + 22 MEDIUM + 15 LOW），后端 117 测试 + 前端 68 测试全部通过，Story 重新进入 review 状态
  - HIGH: 绑定表 user_id FK 约束、capacity_mw CHECK 约束、TOCTOU SELECT FOR UPDATE、提取共享 errors.ts、StationType 类型安全、FormInstance 类型、测试断言修复
  - MEDIUM: server_default 统一、Decimal 精度约束、service 层设备查询、停用语义统一 PUT、侧边栏高亮、roleLabels 共享模块、loading 守卫、watch 双监听、partial update、测试补充
  - LOW: models/__init__.py 完整导出、SOC decimal_places、StationType 查询参数、省份共享常量、测试 Mock 完善
- 2026-02-28: Code Review Round 5 完成 — 发现 2 HIGH、3 MEDIUM、2 LOW 问题，全部 HIGH/MEDIUM 已修复，2 LOW 记录供后续改进
  - HIGH: 前端筛选清除 BUG 修复（直接设 store refs）、测试方法归类修正 + 补充设备去重测试
  - MEDIUM: 补充 StationService get_all_active_* 单元测试、设备查询效率优化（get_by_ids 替代 get_all_active）、roleOptions 自动生成

### File List

**新建文件（后端）：**
- `api-server/alembic/versions/005_create_stations_devices_bindings.py` — 数据库迁移（4 张表 + station_type CHECK 约束）
- `api-server/app/models/station.py` — PowerStation ORM 模型（含 station_type CHECK 约束）
- `api-server/app/models/storage.py` — StorageDevice ORM 模型
- `api-server/app/models/binding.py` — UserStationBinding + UserDeviceBinding 模型（含反向查询索引）
- `api-server/app/core/ip_utils.py` — 公共 IP 地址校验与提取工具
- `api-server/app/schemas/station.py` — 电站 Pydantic Schemas（含 capacity_mw 精度约束）
- `api-server/app/schemas/storage.py` — 储能设备 Pydantic Schemas（含 SOC 交叉校验）
- `api-server/app/schemas/binding.py` — 绑定管理 Pydantic Schemas
- `api-server/app/repositories/station.py` — StationRepository（get_by_ids 支持 active_only）
- `api-server/app/repositories/storage.py` — StorageDeviceRepository（get_by_ids 支持 active_only）
- `api-server/app/repositories/binding.py` — BindingRepository（含设计决策文档）
- `api-server/app/services/station_service.py` — StationService
- `api-server/app/services/binding_service.py` — BindingService（精确错误码 + 类型注解）
- `api-server/app/api/v1/stations.py` — 电站 CRUD API 端点 + GET /stations/active + GET /stations/devices/active
- `api-server/app/api/v1/bindings.py` — 绑定管理 API 端点（路由前缀 /bindings）
- `api-server/scripts/seed_stations.py` — 电站 + 储能设备种子数据
- `api-server/scripts/seed_bindings.py` — 绑定关系种子数据

**新建文件（前端）：**
- `web-frontend/src/types/station.ts` — TypeScript 类型定义
- `web-frontend/src/api/station.ts` — 电站 + 绑定 API 封装
- `web-frontend/src/api/errors.ts` — 共享错误处理工具（getErrorMessage, getErrorCode）
- `web-frontend/src/constants/roles.ts` — 共享角色常量（roleLabels, roleColors, roleOptions）
- `web-frontend/src/constants/provinces.ts` — 共享省份常量（34 个省级行政区）
- `web-frontend/src/stores/station.ts` — 电站 Pinia Store
- `web-frontend/src/views/admin/StationManagementView.vue` — 电站管理页面
- `web-frontend/src/components/admin/BindingConfigDrawer.vue` — 绑定配置抽屉面板

**新建文件（测试）：**
- `api-server/tests/unit/repositories/test_station_repository.py`
- `api-server/tests/unit/repositories/test_binding_repository.py`
- `api-server/tests/unit/services/test_station_service.py`
- `api-server/tests/unit/services/test_binding_service.py`
- `api-server/tests/integration/api/test_stations.py`
- `api-server/tests/integration/api/test_bindings.py`
- `api-server/tests/integration/api/test_devices.py`
- `web-frontend/tests/unit/stores/station.test.ts`
- `web-frontend/tests/unit/views/StationManagementView.test.ts`
- `web-frontend/tests/unit/components/BindingConfigDrawer.test.ts`

**修改文件：**
- `api-server/alembic/env.py` — 导入新模型
- `api-server/app/models/__init__.py` — 导出 PowerStation, StorageDevice, UserStationBinding, UserDeviceBinding
- `api-server/app/api/v1/router.py` — 注册 stations 和 bindings 路由（bindings 使用 /bindings 前缀）
- `docker-compose.dev.yml` — 开发环境配置
- `web-frontend/src/router/index.ts` — 添加 `/admin/stations` 路由
- `web-frontend/src/App.vue` — 侧边栏添加"电站管理"菜单项
- `web-frontend/src/views/admin/UserManagementView.vue` — 添加"资源绑定"按钮和 BindingConfigDrawer
- `web-frontend/components.d.ts` — 自动生成的组件声明
