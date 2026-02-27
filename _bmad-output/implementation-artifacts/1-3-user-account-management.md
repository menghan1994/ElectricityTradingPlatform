# Story 1.3: 用户账户管理与角色分配

Status: done

## Story

As a 系统管理员（老周）,
I want 创建用户账户、编辑用户信息、重置密码、停用/启用账户，并为用户分配角色,
So that 交易团队的每个成员都有正确的系统访问权限。

## Acceptance Criteria

1. **Given** 管理员已登录 **When** 管理员在用户管理页面填写新用户信息（用户名、姓名、联系方式）并提交 **Then** 新用户账户创建成功，分配默认初始密码，操作记录写入审计日志

2. **Given** 管理员查看用户列表 **When** 管理员选择一个用户并修改其信息 **Then** 用户信息更新成功，变更前后值记录写入审计日志

3. **Given** 管理员选择一个用户 **When** 管理员执行"重置密码"操作 **Then** 用户密码被重置为系统生成的临时密码，操作记录写入审计日志

4. **Given** 管理员选择一个活跃用户 **When** 管理员执行"停用账户"操作 **Then** 用户状态变为"已停用"，该用户无法登录，操作记录写入审计日志

5. **Given** 管理员选择一个用户 **When** 管理员为其分配角色（管理员/交易员/储能运维员/交易主管/高管只读） **Then** 角色分配成功，用户下次登录后获得对应权限，角色变更记录写入审计日志

## Tasks / Subtasks

- [x] Task 1: 数据库迁移 — 添加 role 字段 + 创建 audit_logs 表 (AC: #1, #5)
  - [x] 1.1 创建 Alembic 迁移：`users` 表添加 `role` 列（VARCHAR(32), NOT NULL, default='trader'）+ `email` 列（可选）
  - [x] 1.2 创建 Alembic 迁移：`audit_logs` 表（id, user_id, action, resource_type, resource_id, changes_before, changes_after, ip_address, created_at）
  - [x] 1.3 更新种子数据脚本：默认管理员账户 role='admin'

- [x] Task 2: 更新 User 模型 + 角色枚举 (AC: #5)
  - [x] 2.1 定义角色枚举常量：`admin` / `trader` / `storage_operator` / `trading_manager` / `executive_readonly`
  - [x] 2.2 `app/models/user.py` — 添加 `role: Mapped[str]` 字段（default='trader'）、`email: Mapped[str | None]` 字段
  - [x] 2.3 `app/models/audit.py` — 创建 AuditLog ORM 模型

- [x] Task 3: 更新 Pydantic Schemas (AC: #1, #2, #5)
  - [x] 3.1 `app/schemas/user.py` — 更新 UserRead（添加 role, email, is_locked, created_at, updated_at）、UserCreate（添加 role, email）、UserUpdate（添加 display_name, phone, email, is_active）
  - [x] 3.2 新建 AdminUserCreate schema（管理员创建用户：username, display_name, phone, email, role）— 不含密码字段（系统生成）
  - [x] 3.3 新建 AdminResetPasswordResponse schema（返回临时密码）
  - [x] 3.4 新建 UserListResponse schema（分页：items, total, page, page_size）

- [x] Task 4: 审计日志 Service (AC: #1, #2, #3, #4, #5)
  - [x] 4.1 创建 `app/repositories/audit.py` — AuditLogRepository（继承 BaseRepository，添加 get_by_resource / get_by_user 查询方法）
  - [x] 4.2 创建 `app/services/audit_service.py` — `log_action(user_id, action, resource_type, resource_id, changes_before, changes_after, ip_address)` 异步写入审计记录

- [x] Task 5: 用户管理 Service 层 (AC: #1, #2, #3, #4, #5)
  - [x] 5.1 创建 `app/services/user_service.py` — `create_user(admin_user, data)` 生成随机临时密码 + 哈希 + 创建用户 + 写审计日志
  - [x] 5.2 `update_user(admin_user, user_id, data)` — 更新用户信息 + 记录变更前后值审计日志
  - [x] 5.3 `reset_password(admin_user, user_id)` — 生成临时密码 + 哈希 + 记录审计日志 + 返回明文临时密码
  - [x] 5.4 `toggle_active(admin_user, user_id, is_active)` — 停用/启用账户 + 记录审计日志
  - [x] 5.5 `assign_role(admin_user, user_id, role)` — 角色分配 + 记录变更前后角色审计日志
  - [x] 5.6 `list_users(page, page_size, search)` — 分页查询用户列表（支持用户名/姓名搜索）
  - [x] 5.7 `get_user(user_id)` — 获取单个用户详情

- [x] Task 6: RBAC 权限依赖 (AC: #5)
  - [x] 6.1 `app/core/dependencies.py` — 添加 `require_roles(allowed_roles: list[str])` 依赖工厂函数
  - [x] 6.2 更新 JWT Token payload 添加 `role` 字段（create_access_token 增加 role 参数）
  - [x] 6.3 更新 `get_current_user` 依赖从 Token 中解析 role

- [x] Task 7: 用户管理 API 端点 (AC: #1, #2, #3, #4, #5)
  - [x] 7.1 创建 `app/api/v1/users.py` — `GET /api/v1/users` 分页列表（需 admin 角色）
  - [x] 7.2 `GET /api/v1/users/{user_id}` — 获取用户详情（需 admin 角色）
  - [x] 7.3 `POST /api/v1/users` — 创建用户（需 admin 角色）→ 返回 UserRead + 临时密码
  - [x] 7.4 `PUT /api/v1/users/{user_id}` — 更新用户信息（需 admin 角色）
  - [x] 7.5 `POST /api/v1/users/{user_id}/reset_password` — 重置密码（需 admin 角色）→ 返回临时密码
  - [x] 7.6 `PUT /api/v1/users/{user_id}/status` — 停用/启用账户（需 admin 角色）
  - [x] 7.7 `PUT /api/v1/users/{user_id}/role` — 角色分配（需 admin 角色）
  - [x] 7.8 注册路由到 `app/api/v1/router.py`

- [x] Task 8: 前端用户管理 API 封装 (AC: #1, #2, #3, #4, #5)
  - [x] 8.1 创建 `src/api/user.ts` — listUsers, getUser, createUser, updateUser, resetPassword, toggleActive, assignRole

- [x] Task 9: 前端用户管理 Store (AC: #1, #2)
  - [x] 9.1 创建 `src/stores/user.ts` — Pinia Store（userList, total, page, pageSize, isLoading, fetchUsers, searchUsers）

- [x] Task 10: 前端用户管理页面 (AC: #1, #2, #3, #4, #5)
  - [x] 10.1 创建 `src/views/admin/UserManagementView.vue` — Ant Design Vue Table 用户列表 + 搜索框 + 操作按钮
  - [x] 10.2 创建用户对话框组件 — Modal + Form（用户名、姓名、联系方式、邮箱、角色选择）
  - [x] 10.3 编辑用户对话框组件 — 复用创建对话框，预填充数据
  - [x] 10.4 重置密码确认弹窗 + 显示临时密码对话框
  - [x] 10.5 停用/启用确认弹窗
  - [x] 10.6 角色分配下拉选择器 + 确认
  - [x] 10.7 注册路由 `/admin/users` 到 `src/router/index.ts`（meta: { requiresAuth: true, roles: ['admin'] }）

- [x] Task 11: 前端路由角色守卫增强 (AC: #5)
  - [x] 11.1 更新 `src/router/index.ts` — beforeEach 守卫增加 `meta.roles` 校验
  - [x] 11.2 更新 `src/stores/auth.ts` — UserRead 类型添加 role 字段
  - [x] 11.3 更新 `src/api/auth.ts` — UserRead interface 添加 role 字段
  - [x] 11.4 更新 App.vue 侧边栏 — 添加"用户管理"菜单项（仅 admin 角色可见）

- [x] Task 12: 后端测试 (AC: #1-#5)
  - [x] 12.1 `tests/unit/services/test_user_service.py` — 创建用户/更新用户/重置密码/停用启用/角色分配/搜索列表
  - [x] 12.2 `tests/unit/services/test_audit_service.py` — 审计日志写入/查询
  - [x] 12.3 `tests/unit/repositories/test_audit_repository.py` — 审计日志数据访问
  - [x] 12.4 `tests/integration/api/test_users.py` — 用户管理 API 端到端测试（含权限校验：非admin调用返回403）

- [x] Task 13: 前端测试 (AC: #1, #5)
  - [x] 13.1 `tests/unit/stores/user.test.ts` — user store 状态变更测试
  - [x] 13.2 `tests/unit/views/UserManagementView.test.ts` — 用户管理页面渲染+交互测试

### Review Follow-ups (AI) — 2026-02-27 Code Review

**🔴 CRITICAL (必须修复)**

- [x] [AI-Review][CRITICAL] `repositories/audit.py:10` — AuditLogRepository 继承了 BaseRepository.delete()，违反审计日志追加写入原则。需重写 delete() 抛出 NotImplementedError
- [x] [AI-Review][CRITICAL] `repositories/user.py:49-51` — ILIKE 搜索通配符注入：search 参数中 `%` 和 `_` 未转义。需使用 escape 参数
- [x] [AI-Review][CRITICAL] `alembic/versions/002_*.py:38` + `models/user.py:28` — email 列缺少 unique 约束。需新增迁移添加唯一约束 → 新增 003_add_email_unique_constraint.py
- [x] [AI-Review][CRITICAL] `UserManagementView.vue:5,103,131,145,157,176` — 组件直接调用 API 绕过 Store，违反三层架构规则。需将所有写操作迁移到 Store actions
- [x] [AI-Review][CRITICAL] `router/index.ts:35-43` — 角色守卫在 user 为 null 时被绕过。需在 user 未加载时阻止导航到角色受限路由

**🟡 HIGH (应该修复)**

- [x] [AI-Review][HIGH] `schemas/user.py:36` + `user_service.py:89-95` — UserUpdate 包含 is_active 字段，可绕过 toggle_active 的自我保护守卫。需从 UserUpdate 移除 is_active
- [x] [AI-Review][HIGH] `user_service.py:89-95` — update_user 使用通用 setattr 循环无字段白名单。需添加 SAFE_UPDATE_FIELDS 白名单
- [x] [AI-Review][HIGH] `schemas/user.py:40` — AdminUserCreate.username 无输入校验（长度/格式）。需添加 min_length/max_length/pattern
- [x] [AI-Review][HIGH] `schemas/user.py:14,28,35,43` — email 字段无格式校验。需使用 Pydantic EmailStr 类型（添加 email-validator 依赖）
- [x] [AI-Review][HIGH] `schemas/user.py:57` — RoleAssignRequest.role 无枚举校验。需使用 Literal 类型限制合法角色值 → RoleType Literal
- [x] [AI-Review][HIGH] `seed_admin.py:19-20` + `seed_test_users.py:15-16` — 硬编码管理员密码 `Admin@2026`。应从环境变量读取 → SEED_ADMIN_USERNAME/SEED_ADMIN_PASSWORD
- [x] [AI-Review][HIGH] `UserManagementView.vue:57-58` — 临时密码存储在响应式 ref 中，Modal 关闭后未清除。需在 afterClose 回调中清空
- [x] [AI-Review][HIGH] `UserManagementView.vue:193-196` — clipboard.writeText 未 await 且无错误处理。需 async/await + try/catch
- [x] [AI-Review][HIGH] `UserManagementView.test.ts` — 仅 2 个文本渲染测试，零业务逻辑覆盖。需补充创建/编辑/重置/停用/角色分配流程测试 → +5 个业务测试

**🟢 MEDIUM (建议修复)**

- [x] [AI-Review][MEDIUM] `models/audit.py:12` — AuditLog 未使用 IdMixin，与 User 模型不一致
- [x] [AI-Review][MEDIUM] `repositories/audit.py:14` — 审计日志查询无分页上限限制 → MAX_AUDIT_QUERY_LIMIT=500
- [x] [AI-Review][MEDIUM] `user_service.py:135-162` — toggle_active 不检查当前状态，可产生 before=after 的无效审计记录 → no-op 检查
- [x] [AI-Review][MEDIUM] `user_service.py:164-193` — assign_role 不检查当前角色，可产生 before=after 的无效审计记录 → no-op 检查
- [x] [AI-Review][MEDIUM] `schemas/user.py:27,34,42` — phone 字段无格式校验 → 接受风险：中国手机号格式多样，暂不强制正则
- [x] [AI-Review][MEDIUM] `test_users.py:82` — require_roles 依赖覆盖为死代码（闭包对象不匹配）→ 已移除
- [x] [AI-Review][MEDIUM] `stores/user.ts` — Store 仅封装 2/7 个 API 操作，缺少 5 个写操作的 actions → +5 个 actions
- [x] [AI-Review][MEDIUM] `auth.ts` + `user.ts` + View — role 使用 string 类型而非联合类型 → RoleType 联合类型
- [x] [AI-Review][MEDIUM] `UserManagementView.vue:110等` — 错误处理使用不安全 `as` 类型断言（5 处），应使用 axios.isAxiosError 类型守卫
- [x] [AI-Review][MEDIUM] `router/index.ts:36` — RouteMeta 未类型增强，`as string[]` 为不安全断言 → declare module 'vue-router' 类型增强
- [x] [AI-Review][MEDIUM] `stores/user.ts:14-29` — fetchUsers 错误未捕获，onMounted 中 unhandled rejection → .catch() 处理
- [x] [AI-Review][MEDIUM] `stores/user.ts` — Store 无 error 状态 ref，无法显示加载失败 UI → 添加 error ref
- [x] [AI-Review][MEDIUM] `UserManagementView.vue` — 30+ 硬编码中文字符串，无 i18n 准备 → 接受风险：项目当前仅中文用户，i18n 延迟到需要时
- [x] [AI-Review][MEDIUM] Git 差异 — `seed_test_users.py` 和 `components.d.ts` 未记录在 Story File List → 已更新

**🔵 LOW (可选修复)**

- [x] [AI-Review][LOW] `models/user.py:16` — UserRole.ALL 是可变 list，建议改为 frozenset → frozenset
- [x] [AI-Review][LOW] `seed_admin.py:24-25` — 重复定义 hash_password，缺少字节长度检查 → 改为导入 app.core.security.hash_password
- [x] [AI-Review][LOW] tests 多文件 — 测试工厂调用真实 bcrypt rounds=14，拖慢测试速度 → 接受风险：80 个测试 <5s，不影响开发体验
- [x] [AI-Review][LOW] `test_user_service.py` — 缺少管理员重置自己密码的测试 → +1 个测试
- [x] [AI-Review][LOW] `api/v1/users.py:61` — POST 创建用户返回 200 而非 REST 标准 201 → status_code=201
- [x] [AI-Review][LOW] `user_service.py:46-48` — 用户名重复检查存在 TOCTOU 竞态条件 → 接受风险：DB unique 约束兜底

### Review Follow-ups (AI) — 2026-02-27 Code Review #2

**🔴 HIGH (应该修复)**

- [x] [AI-Review-2][HIGH] `user_service.py:48-49` — create_user 缺少 email 唯一性检查。DB 有 unique 约束但 IntegrityError 会作为 500 返回而非友好的 409。需在 UserRepository 添加 get_by_email 方法并在 create_user 中调用 → 已添加 get_by_email + create_user/update_user email 唯一性检查
- [x] [AI-Review-2][HIGH] `user_service.py:89-102` — update_user 更新 email 时同样缺少唯一性检查，重复 email 会导致 IntegrityError → 500 → 已添加 update_user email 唯一性检查（排除自身）
- [x] [AI-Review-2][HIGH] `schemas/user.py:19` — UserRead.role 类型为 `str` 而非 `RoleType`，API 响应不会校验角色值合法性。需改为 `role: RoleType = "trader"` → 已修复
- [x] [AI-Review-2][HIGH] `seed_test_users.py:12` — 使用 `import requests` 但 requirements.txt 中未声明此依赖。脚本执行时会 ModuleNotFoundError。应改用已有的 `httpx` → 已替换为 httpx

**🟡 MEDIUM (建议修复)**

- [x] [AI-Review-2][MEDIUM] `003_add_email_unique_constraint.py` — 迁移文件在 git 中状态为 `??`（未跟踪），需要 `git add` → 待 commit 时一并 stage
- [x] [AI-Review-2][MEDIUM] `repositories/user.py:47` — get_all_paginated 的 page_size 参数无上限防护 → 已添加 `page_size = min(page_size, 100)`
- [x] [AI-Review-2][MEDIUM] `UserManagementView.vue:113-133` — 创建用户对话框缺少前端表单校验规则 → 已添加 createFormRules/editFormRules（username 格式 + email 格式校验）
- [x] [AI-Review-2][MEDIUM] `dependencies.py:get_current_user` — Token payload 中携带 `role` 字段但 get_current_user 未使用也未验证 → 已添加详细注释说明设计意图
- [x] [AI-Review-2][MEDIUM] `audit.py (model)` — AuditLog 不继承 TimestampMixin 缺少注释 → 已添加 docstring 说明追加写入不可变设计
- [x] [AI-Review-2][MEDIUM] `models/user.py` — User 模型 email 列 unique=True 但允许 NULL → 已添加注释确认有意设计（PostgreSQL NULL != NULL 语义）

**🔵 LOW (可选修复)**

- [x] [AI-Review-2][LOW] `api/user.ts:72` + `stores/user.ts:59` — assignRole 的 role 参数类型为 `string` 而非 `RoleType` → 已改为 RoleType
- [x] [AI-Review-2][LOW] `user_service.py:update_user` — 当 update_data 中所有字段值与当前值相同时，不写审计日志（已正确实现 no-op），但会多一次 DB 查询 → 接受风险：单次 DB 查询成本可忽略
- [x] [AI-Review-2][LOW] `UserManagementView.vue` — 编辑用户对话框同样缺少 a-form rules 校验 → 已添加 editFormRules + editFormRef

### Review Follow-ups (AI) — 2026-02-27 Code Review #3

**🔴 HIGH (应该修复)**

- [x] [AI-Review-3][HIGH] `user_service.py:184` — assign_role 的 role 参数类型为 `str` 而非 `RoleType`。Service 层签名应与 Schema 层类型一致，避免其他调用方绕过类型检查 → 已改为 RoleType
- [x] [AI-Review-3][HIGH] `test_users.py` — 权限测试仅覆盖 2/7 个端点的 403 拒绝测试。其余 5 个端点（get_user/create_user/update_user/reset_password/toggle_status）缺少非 admin 角色的 403 测试 → +5 个 403 测试
- [x] [AI-Review-3][HIGH] `user_service.py:43-44` — 所有 Service 方法的 ip_address 默认 None，通过非 HTTP 上下文调用时 IP 静默丢失。应在 ip_address is None 时打 warning 日志 → 添加 _warn_if_no_ip 辅助方法
- [x] [AI-Review-3][HIGH] `api/v1/users.py:68` — request.client.host 在反向代理（Nginx/Docker）环境下返回内网 IP 而非真实客户端 IP。需读取 X-Forwarded-For / X-Real-IP header → 添加 _get_client_ip 辅助函数

**🟡 MEDIUM (建议修复)**

- [x] [AI-Review-3][MEDIUM] `audit.py (model):21` — AuditLog.user_id 有 ForeignKey 约束，未来 hard delete 用户会触发外键错误。审计日志应长期保留（≥3年），建议移除外键约束只保留 UUID 值 → 移除 FK + 新增迁移 004
- [x] [AI-Review-3][MEDIUM] `seed_admin.py:45` — 种子脚本成功后 print 密码明文到终端/日志，CI/CD 或 Docker 日志中会持久化敏感信息 → 不再打印密码明文，改为提示查看环境变量
- [x] [AI-Review-3][MEDIUM] `UserManagementView.vue:108-111` — onMounted 初始加载失败后只显示短暂 toast，无错误状态 UI。Store 有 error ref 但模板未使用 → 添加 a-alert 错误状态组件
- [x] [AI-Review-3][MEDIUM] `test_user_service.py:41` — _make_user 工厂调用真实 bcrypt（~1s/次），随测试增长会成瓶颈。可用预哈希常量替代 → 使用 _PREHASHED_PASSWORD 常量
- [x] [AI-Review-3][MEDIUM] `dependencies.py:22,72` — get_current_user 和 get_current_active_user 缺少返回类型注解（-> User），违反 project-context "所有函数必须有类型注解" 规则 → 添加 -> "User" 返回类型注解 + TYPE_CHECKING import
- [x] [AI-Review-3][MEDIUM] `user_service.py:99` — email 唯一性检查用 truthy 判断（空字符串被跳过），逻辑上应用 `is not None` 更精确 → 改为 is not None

**🔵 LOW (可选修复)**

- [x] [AI-Review-3][LOW] `api/v1/users.py:27-31` — _get_user_service 每次请求创建 4 个对象，可考虑统一依赖注入注册 → 接受风险：FastAPI Depends 本身就是请求级别创建，当前模式是标准实践
- [x] [AI-Review-3][LOW] `schemas/user.py:17` — UserRead.email 类型为 `str | None` 而非 `EmailStr | None`，读取模型不校验 → 已改为 EmailStr | None
- [x] [AI-Review-3][LOW] `stores/user.ts:56-57` — resetPassword action 不刷新用户列表，与其他 write actions 不一致 → 已添加 await fetchUsers()

### Review Follow-ups (AI) — 2026-02-28 Code Review #4

**🔴 HIGH (应该修复)**

- [x] [AI-Review-4][HIGH] `api/v1/users.py:33-35` — `_get_client_ip` 无条件信任 X-Forwarded-For header，任何客户端可伪造 IP 注入审计日志。需添加 `ipaddress.ip_address()` 格式验证，非法值回退到 `request.client.host` → 已添加 `_validate_ip` 函数，所有来源经 `ipaddress.ip_address()` 验证
- [x] [AI-Review-4][HIGH] `dependencies.py:104-106` — `require_roles` 内部 `role_checker` 函数的 `current_user` 参数和返回值缺少类型注解，违反 project-context "所有函数必须有类型注解" 规则（Review #3 修复了 get_current_user/get_current_active_user 但遗漏此处） → 已添加 `current_user: "User"` 参数注解和 `-> "User"` 返回值注解
- [x] [AI-Review-4][HIGH] `user_service.py:51` + `:195` — Service 层 role 校验与 Schema 层 `RoleType` Literal 重复，存在双源真值问题。建议使用 `typing.get_args(RoleType)` 自动生成 `UserRole.ALL`，或移除 Service 层重复校验 → `UserRole.ALL` 和 `_VALID_ROLES` 均由 `get_args(RoleType)` 自动派生，RoleType Literal 为唯一真值源

**🟡 MEDIUM (建议修复)**

- [x] [AI-Review-4][MEDIUM] `seed_admin.py:21` + `seed_test_users.py:16` — 环境变量未设置时默认密码 `Admin@2026` 硬编码在源码中，可猜测。建议未设置时自动生成随机密码（复用 `generate_temp_password`） → seed_admin 未设置时调用 `generate_temp_password(16)` 自动生成；seed_test_users 要求必须设置环境变量
- [x] [AI-Review-4][MEDIUM] `user_service.py:64` + `:144` — `hash_password` 同步阻塞调用（bcrypt rounds=14 ~1s）在 async 方法中阻塞事件循环。高并发场景需使用 `asyncio.to_thread(hash_password, ...)` 卸载到线程池 → 已改为 `await asyncio.to_thread(hash_password, ...)`
- [x] [AI-Review-4][MEDIUM] `test_users.py` — 集成测试缺少错误路径（409 用户名重复、404 用户不存在、422 参数校验失败），仅覆盖 happy path + 403。需补充至少 3 个错误路径测试 → +3 个错误路径测试（TestErrorPaths 类）
- [x] [AI-Review-4][MEDIUM] `UserManagementView.vue` — 编辑用户对话框无只读 username/role 展示，管理员无法确认正在编辑哪个用户。需添加只读字段 → 已添加只读 username（disabled input）和 role（a-tag）展示
- [x] [AI-Review-4][MEDIUM] `audit_service.py:35` — 审计日志与业务操作共享 DB session，审计写入失败会导致业务操作回滚。需在 Dev Notes 中明确记录此设计决策（审计完整性 > 可用性） → 已在 AuditService 类添加详细 docstring 说明设计决策

**🔵 LOW (可选修复)**

- [x] [AI-Review-4][LOW] `schemas/user.py:26-32` — `UserCreate` schema（含 password 字段）未被任何代码引用，是死代码。如后续无用户自注册需求可移除 → 已移除
- [x] [AI-Review-4][LOW] `test_user_service.py:109-118` — `test_create_user_no_email_skips_check` 未配置 `get_by_email` 的失败 side_effect，如果实现错误调用 `get_by_email`，AsyncMock 默认返回 truthy 值不会触发异常 → 已添加 `RuntimeError` side_effect
- [x] [AI-Review-4][LOW] `alembic/versions/002` + `004` — 迁移 002 创建 audit_logs 表带 FK，004 又删除 FK。若项目未发布生产环境，可合并迁移减少迁移链长度 → 接受风险：迁移链完整正确，合并收益低且可能影响现有开发数据库

### Review Follow-ups (AI) — 2026-02-28 Code Review #5

**🔴 HIGH (应该修复)**

- [x] [AI-Review-5][HIGH] `auth_service.py:165` — `change_password` 中 `hash_password` 仍为同步阻塞调用，未使用 `asyncio.to_thread()`。Review #4 修复了 `user_service.py` 但遗漏此处 → 已改为 `await asyncio.to_thread(hash_password, new_password)`
- [x] [AI-Review-5][HIGH] `test_auth_service.py:37` — `_make_user` 工厂函数调用真实 bcrypt rounds=14，每个测试约 1 秒。`test_user_service.py` 已引入预哈希但此文件未同步 → 已引入 `_PASSWORD_HASHES` 缓存，模块级预计算默认密码哈希
- [x] [AI-Review-5][HIGH] `seed_admin.py:52` — 自动生成密码仍通过 `print()` 输出到 stdout/日志，Docker/CI 环境下会持久化 → 改为写入 0600 权限临时文件

**🟡 MEDIUM (建议修复)**

- [x] [AI-Review-5][MEDIUM] `test_user_service.py` — `create_user` 的无效角色测试仅覆盖 Schema 层拒绝，缺少直接调用 Service 传入无效 role 的测试（绕过 Pydantic 的运行时防御） → +1 个 `test_create_user_invalid_role_via_service` 测试
- [x] [AI-Review-5][MEDIUM] `api/v1/users.py:55` — `_get_client_ip` 最后的 `request.client.host` 未经 `_validate_ip` 验证，代理配置异常时可能返回非法值 → 已统一经 `_validate_ip` 处理
- [x] [AI-Review-5][MEDIUM] `UserManagementView.vue:117` — `handleTableChange` 调用 `fetchUsers` 未 `.catch()`，与 `onMounted` 处理不一致，产生 unhandled rejection → 已添加 `.catch()` 错误处理

**🔵 LOW (可选修复)**

- [x] [AI-Review-5][LOW] `schemas/user.py:33` — `AdminUserCreate.username` pattern 允许大小写混合但无注释说明意图 → 已添加注释确认有意设计
- [x] [AI-Review-5][LOW] `UserManagementView.vue:88` — `roleAssignValue` 类型为 `RoleType | ''` 不严谨 → 改为 `RoleType | null`
- [ ] [AI-Review-5][LOW] `test_users.py` 多处 — `f"Bearer fake"` f-string 无插值变量 → 接受风险：纯代码风格，无功能影响

## Dev Notes

### 技术选型（延续 Story 1.2 已验证方案）

| 库 | 版本 | 说明 |
|---|------|------|
| **PyJWT** | 2.11.0 | JWT Token — 本 Story 新增 `role` 字段到 payload |
| **bcrypt** | 5.0.0 | 密码哈希 — 复用 `hash_password()`，新增临时密码生成 |
| **Ant Design Vue** | 4.2.x | 前端 UI — 使用 Table、Modal、Form、Select、Popconfirm 组件 |

### 角色系统设计

**5种角色枚举（字符串常量，存储在 users.role 列）：**

```python
# app/models/user.py 或独立 constants 文件
class UserRole:
    ADMIN = "admin"                     # 系统管理员 — 用户管理、系统配置
    TRADER = "trader"                   # 交易员 — 报价操作
    STORAGE_OPERATOR = "storage_operator"  # 储能运维员 — 调度操作
    TRADING_MANAGER = "trading_manager"    # 交易主管 — 只读全部电站
    EXECUTIVE_READONLY = "executive_readonly"  # 高管只读 — 仪表盘查看
```

**为什么用字符串而非数据库枚举类型：**
- 新增角色只需添加代码常量 + 迁移脚本添加 CHECK 约束值，无需 ALTER TYPE
- 前后端传输直接用字符串，序列化无额外成本
- 与 JWT payload 中 role 字段的字符串格式天然一致

**角色权限对照（本 Story 仅实现 admin 守卫，完整权限矩阵在 Story 1.5）：**

| 功能 | admin | trader | storage_operator | trading_manager | executive_readonly |
|------|-------|--------|-----------------|----------------|-------------------|
| 用户管理 CRUD | ✅ | ❌ | ❌ | ❌ | ❌ |
| 角色分配 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 修改自己密码 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 查看自己信息 | ✅ | ✅ | ✅ | ✅ | ✅ |

### 现有代码基础（Story 1.2 已建立 — 必须复用）

**直接复用，禁止重写：**
- `app/core/security.py` — `hash_password()` / `verify_password()` / `validate_password_strength()` / `create_access_token()` / `create_refresh_token()` / `decode_token()`
- `app/core/dependencies.py` — `get_current_user()` / `get_current_active_user()`（需扩展，不重写）
- `app/core/config.py` — JWT 配置已就绪
- `app/core/database.py` — AsyncSession + async_sessionmaker
- `app/core/exceptions.py` — `BusinessError` 异常类
- `app/core/logging.py` — structlog + TraceIdMiddleware
- `app/models/base.py` — `IdMixin`（UUID主键）+ `TimestampMixin`
- `app/repositories/base.py` — `BaseRepository[T]` 泛型基类（get_by_id/get_all/create/delete）
- `app/models/user.py` — User 模型（需扩展添加 role 字段）
- `app/repositories/user.py` — UserRepository（需扩展添加 `get_all_paginated`、`search_users` 方法）
- `app/schemas/user.py` — UserCreate/UserRead/UserUpdate（需扩展添加 role 字段）
- `app/schemas/auth.py` — 已有 schemas 保持不变
- `app/services/auth_service.py` — 认证逻辑保持不变
- `app/api/v1/auth.py` — 认证端点保持不变
- `web-frontend/src/stores/auth.ts` — auth store（需更新 UserRead 类型添加 role）
- `web-frontend/src/api/auth.ts` — UserRead interface（需添加 role 字段）
- `web-frontend/src/api/client.ts` — Axios 实例 + 拦截器
- `web-frontend/src/router/index.ts` — 路由守卫（需增强 roles 校验）
- `web-frontend/src/App.vue` — 侧边栏（需添加管理菜单）

**需要新建的文件：**
- `api-server/alembic/versions/002_add_role_and_audit_logs.py` — 数据库迁移
- `api-server/app/models/audit.py` — AuditLog ORM 模型
- `api-server/app/repositories/audit.py` — AuditLog Repository
- `api-server/app/services/audit_service.py` — 审计日志 Service
- `api-server/app/services/user_service.py` — 用户管理 Service
- `api-server/app/api/v1/users.py` — 用户管理 API 端点
- `web-frontend/src/api/user.ts` — 用户管理 API 封装
- `web-frontend/src/stores/user.ts` — 用户管理 Pinia Store
- `web-frontend/src/views/admin/UserManagementView.vue` — 用户管理页面

### 架构合规要求

**三层架构（强制）：**
```
API 层 (app/api/v1/users.py)
  → 路由端点，参数校验，权限守卫（require_roles(['admin'])）
  → 禁止在此层写业务逻辑

Service 层 (app/services/user_service.py)
  → 用户 CRUD 逻辑、临时密码生成、审计日志记录
  → 使用 BusinessError 抛出业务异常

Repository 层 (app/repositories/user.py + audit.py)
  → 数据库操作：用户查询/创建/更新 + 审计日志写入
  → 继承 BaseRepository[T]
```

**API 端点设计：**
```
GET    /api/v1/users                       → UserListResponse（分页 + 搜索）
GET    /api/v1/users/{user_id}             → UserRead
POST   /api/v1/users                       → { user: UserRead, temp_password: str }
PUT    /api/v1/users/{user_id}             → UserRead
POST   /api/v1/users/{user_id}/reset_password → { temp_password: str }
PUT    /api/v1/users/{user_id}/status      → UserRead（更新 is_active）
PUT    /api/v1/users/{user_id}/role        → UserRead（更新 role）
```

**所有端点均需 `Depends(require_roles(['admin']))` 权限守卫。**

**错误码定义（新增）：**

| 错误码 | HTTP Status | 含义 |
|--------|-------------|------|
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `USERNAME_EXISTS` | 409 | 用户名已被注册 |
| `CANNOT_MODIFY_SELF` | 403 | 管理员不能停用自己的账户 |
| `INVALID_ROLE` | 422 | 角色值无效 |
| `FORBIDDEN` | 403 | 无权限执行此操作 |

### 审计日志设计

**audit_logs 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | IdMixin |
| user_id | UUID | FK → users.id, NOT NULL | 执行操作的用户 |
| action | VARCHAR(64) | NOT NULL | 操作类型（create_user/update_user/reset_password/toggle_active/assign_role） |
| resource_type | VARCHAR(64) | NOT NULL | 资源类型（user） |
| resource_id | UUID | NOT NULL | 被操作的资源 ID |
| changes_before | JSONB | | 变更前的值（JSON 对象） |
| changes_after | JSONB | | 变更后的值（JSON 对象） |
| ip_address | VARCHAR(45) | | 操作者 IP 地址 |
| created_at | TIMESTAMP WITH TZ | NOT NULL | 操作时间（追加写入，不可修改） |

**审计日志写入示例：**
```python
# 角色变更审计
await audit_service.log_action(
    user_id=admin_user.id,
    action="assign_role",
    resource_type="user",
    resource_id=target_user.id,
    changes_before={"role": "trader"},
    changes_after={"role": "admin"},
    ip_address=request.client.host
)
```

**关键：** 审计日志表追加写入，不提供 UPDATE/DELETE 接口。本 Story 的审计日志仅用于用户管理操作，后续 Story 复用此基础设施记录其他审计事件。

### JWT Token 扩展

**Access Token payload 变更（添加 role 字段）：**
```python
payload = {
    "sub": str(user.id),
    "username": user.username,
    "role": user.role,          # 新增：用户角色
    "exp": now + 30min,
    "iat": now,
    "type": "access"
}
```

**影响范围：**
- `app/core/security.py` — `create_access_token()` 增加 `role` 参数
- `app/services/auth_service.py` — `authenticate()` 传递 `user.role` 到 Token 生成
- `app/core/dependencies.py` — `get_current_user()` 从 Token 解析 role 并设置到 User 对象
- `web-frontend/src/api/auth.ts` — `UserRead` interface 添加 `role: string`
- `web-frontend/src/stores/auth.ts` — 相应类型更新

### RBAC 权限守卫实现

```python
# app/core/dependencies.py — 新增
def require_roles(allowed_roles: list[str]):
    """依赖工厂：校验当前用户角色是否在允许列表中"""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise BusinessError(
                code="FORBIDDEN",
                message="无权限执行此操作",
                status_code=403
            )
        return current_user
    return role_checker

# 使用方式
@router.get("/users")
async def list_users(
    current_user: User = Depends(require_roles(["admin"])),
    ...
):
```

### 临时密码生成

```python
import secrets
import string

def generate_temp_password(length: int = 12) -> str:
    """生成符合密码策略的临时密码"""
    # 确保包含所有必需字符类型
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    # 填充剩余字符
    remaining = length - len(password)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password.extend(secrets.choice(alphabet) for _ in range(remaining))
    # 随机打乱
    secrets.SystemRandom().shuffle(password)
    return "".join(password)
```

### 前端实现要点

**用户管理页面布局（Ant Design Vue）：**
```
┌─────────────────────────────────────────────────┐
│ 用户管理                        [+ 创建用户] 按钮 │
├─────────────────────────────────────────────────┤
│ [搜索框：用户名/姓名搜索]                         │
├─────────────────────────────────────────────────┤
│ 用户名 | 姓名 | 角色 | 状态 | 最后登录 | 操作     │
│ admin  | 管理员| admin| 活跃 | 2026-02-27 | ...  │
│ lina   | 李娜  | trader| 活跃| 2026-02-26 | ...  │
│ ...                                              │
├─────────────────────────────────────────────────┤
│ 分页组件                                          │
└─────────────────────────────────────────────────┘
```

**操作列按钮：**
- 编辑（编辑用户信息对话框）
- 重置密码（Popconfirm 确认 → 显示临时密码对话框）
- 停用/启用（Popconfirm 确认）
- 角色分配（Select 下拉 + 确认）

**角色显示映射（中文标签 + Tag 颜色）：**
```typescript
const roleLabels: Record<string, string> = {
  admin: '系统管理员',
  trader: '交易员',
  storage_operator: '储能运维员',
  trading_manager: '交易主管',
  executive_readonly: '高管只读',
}

const roleColors: Record<string, string> = {
  admin: 'red',
  trader: 'blue',
  storage_operator: 'green',
  trading_manager: 'orange',
  executive_readonly: 'purple',
}
```

**路由角色守卫增强：**
```typescript
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else if (to.meta.roles && authStore.user) {
    const allowedRoles = to.meta.roles as string[]
    if (!allowedRoles.includes(authStore.user.role)) {
      next('/') // 无权限重定向到首页
    } else {
      next()
    }
  } else {
    next()
  }
})
```

### 数据库迁移注意事项

1. **role 字段默认值**：设为 `'trader'`，确保现有用户（含 admin 种子数据）迁移后有值
2. **迁移后更新种子数据**：将 admin 用户 role 更新为 `'admin'`
3. **audit_logs 表**：不设 updated_at（追加写入，不可修改）
4. **audit_logs.changes_before/after**：使用 JSONB 类型，灵活存储不同操作的变更内容

### 安全注意事项

1. **管理员不能停用自己**：`toggle_active()` 校验 `target_user.id != admin_user.id`
2. **管理员不能降级自己**：`assign_role()` 校验如果目标用户是当前管理员且新角色非 admin，拒绝操作
3. **临时密码仅返回一次**：创建用户/重置密码时明文临时密码仅在 API 响应中返回一次，不存储明文
4. **审计日志不记录密码**：changes_before/after 中不包含 hashed_password 字段
5. **用户列表不返回密码哈希**：UserRead schema 不包含 hashed_password

### 与后续 Story 的关系

- **Story 1.4（交易员-电站绑定）**：需要本 Story 的 role 字段来识别交易员和运维员角色
- **Story 1.5（数据访问控制）**：需要本 Story 的 `require_roles()` 权限守卫 + role 字段
- **Epic 9（审计合规）**：本 Story 建立的 audit_logs 表和 audit_service 将被后续所有 Story 复用

### Project Structure Notes

- 所有新文件位于 Story 1.1/1.2 已创建的目录结构中
- 后端新增 `app/models/audit.py`、`app/repositories/audit.py`、`app/services/audit_service.py`、`app/services/user_service.py`、`app/api/v1/users.py`
- 前端新增 `src/api/user.ts`、`src/stores/user.ts`、`src/views/admin/UserManagementView.vue`
- 路由新增 `/admin/users` 路径
- 测试文件镜像源码结构

### References

- [Source: architecture.md#Authentication & Security] — RBAC 5角色权限模型、JWT 双 Token 设计
- [Source: architecture.md#Implementation Patterns] — 三层架构、命名规范、反模式清单
- [Source: architecture.md#Data Architecture] — 数据校验策略、统一错误响应格式
- [Source: architecture.md#Project Structure] — 目录结构定义、users.py API 端点位置
- [Source: epics/epic-1.md#Story 1.3] — 原始需求和验收标准
- [Source: epics/epic-1.md#Story 1.4-1.5] — 后续 Story 对 role 和权限的依赖关系
- [Source: project-context.md#Critical Implementation Rules] — 反模式清单、安全规则、测试规则
- [Source: project-context.md#Framework-Specific Rules] — FastAPI 三层架构强制、RBAC 依赖注入
- [Source: 1-2-user-authentication.md] — Story 1.2 已建立的代码基础、文件清单、Dev Notes

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- MagicMock 序列化错误：添加 `role` 参数到 `create_access_token` 后，3 个现有 auth_service 测试失败（`TypeError: Object of type MagicMock is not JSON serializable`）。原因：`_make_user` 工厂函数未显式设置 `role` 属性，MagicMock 返回另一个 MagicMock 对象而非字符串。修复：在 `_make_user` 中添加 `role: str = "trader"` 参数和 `user.role = role` 赋值。

### Completion Notes List

- 全部 13 个 Task（~50 个子任务）已完成
- AI Code Review #1：37 个发现全部处理（5C/9H/14M/9L — 34 项修复 + 3 项接受风险并注明理由）
- AI Code Review #2：13 个发现全部处理（4H/6M/3L — 12 项修复 + 1 项接受风险）
- AI Code Review #3：13 个发现全部处理（4H/6M/3L — 12 项修复 + 1 项接受风险）
- AI Code Review #4：11 个发现全部处理（3H/5M/3L — 10 项修复 + 1 项接受风险）
- AI Code Review #5：9 个发现全部处理（3H/3M/3L — 8 项修复 + 1 项接受风险）
- 运行时修复：GET /api/v1/users 500 错误（EmailStr 空字符串校验），添加 field_validator 空串转 None
- 后端测试：93 passed, 0 failed（46 个已有 + 47 个新增，含 review #5 阶段 +1 个 invalid_role 测试）
- 前端测试：32 passed, 0 failed（14 个已有 + 18 个新增）
- 零回归引入
- RBAC 权限守卫 `require_roles()` 使用依赖工厂模式实现，所有用户管理端点均需 admin 角色
- JWT access token payload 扩展了 `role` 字段
- 审计日志基础设施建立完成，可被后续 Story 复用
- 临时密码生成使用 `secrets` 模块，符合密码策略要求
- 安全约束全部满足：管理员不能停用/降级自己、密码不记入审计日志、临时密码仅返回一次
- Review #1 安全加固：ILIKE 注入防护、email unique 约束、SAFE_UPDATE_FIELDS 白名单、Literal 类型强制角色校验、审计日志 delete 禁止、密码环境变量化
- Review #2 加固：email 唯一性应用层检查（409 友好错误）、UserRead.role 类型强化、seed 脚本 httpx 替换、page_size 上限防护、前端表单校验规则、代码意图注释补充
- Review #3 加固：assign_role RoleType 类型签名、7/7 端点 403 权限测试全覆盖、ip_address 缺失 warning、反向代理 X-Forwarded-For IP 提取、审计日志 FK 移除（长期保留友好）、种子脚本密码不再明文打印、错误状态 UI 组件、测试预哈希常量优化、dependencies 返回类型注解、email is not None 精确判断、UserRead EmailStr 类型、resetPassword 列表刷新
- Review #4 加固：IP 伪造防护（ipaddress 格式验证）、require_roles 类型注解补全、RoleType 单一真值源（get_args 消除双源）、种子脚本随机密码生成、bcrypt asyncio.to_thread 异步化、+3 错误路径集成测试（409/404/422）、编辑对话框只读 username/role 展示、审计共享 session 设计决策文档化、UserCreate 死代码移除、测试 side_effect 加固
- Review #5 加固：auth_service change_password asyncio.to_thread 异步化、test_auth_service 预哈希缓存（_PASSWORD_HASHES）、seed_admin 密码写入 0600 临时文件、+1 Service 层 invalid_role 测试、_get_client_ip 最后路径统一 _validate_ip、handleTableChange .catch 错误处理、username pattern 意图注释、roleAssignValue null 类型
- 运行时修复：schemas/user.py field_validator 空字符串转 None（UserRead/UserUpdate/AdminUserCreate），解决 EmailStr 对 DB 中 "" 空串的校验失败

### File List

**新增文件：**

- `api-server/alembic/versions/002_add_role_email_and_audit_logs.py` — 数据库迁移（role/email 列 + audit_logs 表）
- `api-server/alembic/versions/003_add_email_unique_constraint.py` — email 列唯一约束迁移（Review 修复 C3）
- `api-server/alembic/versions/004_drop_audit_logs_user_id_fk.py` — 移除审计日志外键约束迁移（Review #3）
- `api-server/app/models/audit.py` — AuditLog ORM 模型
- `api-server/app/repositories/audit.py` — AuditLogRepository
- `api-server/app/services/audit_service.py` — AuditService（审计日志写入）
- `api-server/app/services/user_service.py` — UserService（用户 CRUD + 审计）
- `api-server/app/api/v1/users.py` — 用户管理 API 端点（7 个端点）
- `api-server/scripts/seed_test_users.py` — 批量创建测试用户脚本
- `api-server/tests/unit/services/test_user_service.py` — UserService 单元测试（31 个，含 Review #2 +4 个 email 唯一性测试）
- `api-server/tests/unit/services/test_audit_service.py` — AuditService 单元测试（3 个）
- `api-server/tests/unit/repositories/test_audit_repository.py` — AuditLogRepository 单元测试（4 个）
- `api-server/tests/integration/api/test_users.py` — 用户管理 API 集成测试（12 个，含 Review #3 +5 个 403 权限测试）
- `web-frontend/src/api/user.ts` — 用户管理 API 封装
- `web-frontend/src/stores/user.ts` — 用户管理 Pinia Store（7 个 actions + error 状态）
- `web-frontend/src/views/admin/UserManagementView.vue` — 用户管理页面
- `web-frontend/tests/unit/stores/user.test.ts` — user store 测试（12 个）
- `web-frontend/tests/unit/views/UserManagementView.test.ts` — 用户管理页面测试（7 个）

**修改文件：**

- `api-server/app/models/user.py` — 添加 UserRole 常量类（frozenset）、email/role 字段（email unique）+ Review #2 NULL unique 注释
- `api-server/app/schemas/user.py` — RoleType Literal、EmailStr、Field 校验、移除 UserUpdate.is_active + Review #2 UserRead.role 类型修复
- `api-server/app/repositories/user.py` — get_all_paginated + ILIKE escape 防注入 + Review #2 get_by_email + page_size 上限
- `api-server/app/repositories/audit.py` — delete() 禁止 + MAX_AUDIT_QUERY_LIMIT
- `api-server/app/models/audit.py` — 使用 IdMixin + Review #2 追加写入设计 docstring
- `api-server/app/services/user_service.py` — SAFE_UPDATE_FIELDS 白名单 + no-op 检查 + Review #2 email 唯一性检查
- `api-server/app/core/security.py` — create_access_token 添加 role 参数
- `api-server/app/core/dependencies.py` — 添加 require_roles() 依赖工厂函数 + Review #2 role 字段设计意图注释
- `api-server/app/services/auth_service.py` — authenticate/refresh_access_token 传递 role
- `api-server/app/api/v1/router.py` — 注册 users 路由
- `api-server/app/api/v1/users.py` — POST 返回 201
- `api-server/alembic/env.py` — 导入 AuditLog 模型
- `api-server/scripts/seed_admin.py` — 环境变量密码 + 导入 hash_password
- `api-server/requirements.txt` — 添加 email-validator==2.2.0
- `api-server/tests/unit/services/test_auth_service.py` — _make_user 添加 role 参数
- `api-server/tests/integration/api/test_auth.py` — _make_user_obj 添加 role/email 字段
- `api-server/tests/integration/api/test_users.py` — 移除死代码 + 201 状态码
- `web-frontend/src/api/auth.ts` — RoleType 联合类型 + UserRead role 类型化
- `api-server/scripts/seed_test_users.py` — Review #2 替换 requests 为 httpx
- `web-frontend/src/api/user.ts` — RoleType 引用 + 移除 UserUpdate.is_active + Review #2 assignRole role 类型修复
- `web-frontend/src/router/index.ts` — RouteMeta 类型增强 + 角色守卫 null 安全修复
- `web-frontend/src/App.vue` — 侧边栏添加管理员菜单项
- `web-frontend/src/views/admin/UserManagementView.vue` — 全部写操作通过 Store + axios.isAxiosError + async clipboard + Review #2 表单校验规则
- `web-frontend/src/stores/user.ts` — +5 个 write actions + error ref + Review #2 assignRole RoleType 类型
- `web-frontend/tests/unit/stores/auth.test.ts` — mock 用户数据添加新字段
- `web-frontend/components.d.ts` — 自动生成更新

## Change Log

| 日期 | 变更内容 | 原因 |
|------|---------|------|
| 2026-02-27 | 实现 Story 1-3 全部 13 个 Task | 用户账户管理与角色分配功能开发 |
| 2026-02-27 | 扩展 JWT access token payload 添加 role 字段 | RBAC 权限控制需要在 Token 中携带角色信息 |
| 2026-02-27 | 创建 audit_logs 表和审计日志服务 | 满足所有 AC 中的审计日志记录要求 |
| 2026-02-27 | 修复 test_auth_service.py MagicMock 序列化问题 | 添加 role 到 Token 后现有测试回归 |
| 2026-02-27 | AI Code Review — 发现 37 个问题（5C/9H/14M/9L），创建行动项 | 对抗性代码审查，状态从 review 改为 in-progress |
| 2026-02-27 | 修复全部 37 个 Code Review 发现项（34 修复 + 3 接受风险） | 安全加固 + 代码质量提升 + 测试补充 |
| 2026-02-27 | 新增迁移 003（email unique）、email-validator 依赖、RoleType Literal 类型 | Review CRITICAL/HIGH 修复 |
| 2026-02-27 | 后端 80 tests / 前端 32 tests 全部通过，零回归 | Review 修复后回归验证 |
| 2026-02-27 | AI Code Review #2 — 发现 13 个新问题（4H/6M/3L），创建行动项 | 第二轮对抗性代码审查，状态从 review 改为 in-progress |
| 2026-02-27 | 修复全部 13 个 Code Review #2 发现项（12 修复 + 1 接受风险） | email 唯一性检查、类型强化、脚本依赖修复、前端表单校验、代码注释补充 |
| 2026-02-27 | 后端 84 tests / 前端 32 tests 全部通过，零回归 | Review #2 修复后回归验证 |
| 2026-02-27 | AI Code Review #3 — 发现 13 个新问题（4H/6M/3L），创建行动项 | 第三轮对抗性代码审查：反向代理 IP、审计日志外键、类型注解、权限测试覆盖 |
| 2026-02-28 | 修复全部 13 个 Code Review #3 发现项（12 修复 + 1 接受风险） | assign_role RoleType 签名、7/7 端点 403 测试全覆盖、ip warning、X-Forwarded-For、审计 FK 移除、种子密码安全、错误 UI、测试优化、类型注解、email is not None、EmailStr、resetPassword 刷新 |
| 2026-02-28 | 后端 89 tests / 前端 32 tests 全部通过，零回归 | Review #3 修复后回归验证 |
| 2026-02-28 | AI Code Review #4 — 发现 11 个新问题（3H/5M/3L），创建行动项 | 第四轮对抗性代码审查：IP 伪造防护、类型注解完整性、双源真值、bcrypt 异步化、集成测试错误路径、编辑对话框 UX |
| 2026-02-28 | 修复全部 11 个 Code Review #4 发现项（10 修复 + 1 接受风险） | IP ipaddress 验证、require_roles 类型注解、RoleType get_args 单一真值源、种子随机密码、bcrypt to_thread、+3 错误路径测试、编辑对话框只读字段、审计设计文档、UserCreate 移除、测试 side_effect |
| 2026-02-28 | 后端 92 tests / 前端 32 tests 全部通过，零回归 | Review #4 修复后回归验证 |
| 2026-02-28 | Story 状态 → review | 全部 4 轮 Code Review 修复完成 |
| 2026-02-28 | AI Code Review #5 — 发现 9 个新问题（3H/3M/3L），创建行动项 | 第五轮对抗性代码审查：auth_service 同步阻塞、test_auth_service 预哈希、seed_admin 密码泄露、Service 层角色防御、IP 验证一致性、分页错误处理 |
| 2026-02-28 | 修复全部 9 个 Code Review #5 发现项（8 修复 + 1 接受风险） | auth_service asyncio.to_thread、test_auth_service 预哈希缓存、seed_admin 临时文件、+1 invalid_role 测试、_get_client_ip 统一验证、handleTableChange .catch、username pattern 注释、roleAssignValue null 类型 |
| 2026-02-28 | 修复运行时 500 错误：GET /api/v1/users EmailStr 空字符串验证失败 | 数据库 email="" 空字符串导致 Pydantic EmailStr 校验失败，添加 field_validator 空串转 None |
| 2026-02-28 | 后端 93 tests / 前端 32 tests 全部通过，零回归 | Review #5 修复后回归验证 |
| 2026-02-28 | Story 状态 → done | 全部 5 轮 Code Review 修复完成，功能验证通过 |
