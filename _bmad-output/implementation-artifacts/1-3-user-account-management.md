# Story 1.3: 用户账户管理与角色分配

Status: ready-for-dev

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

- [ ] Task 1: 数据库迁移 — 添加 role 字段 + 创建 audit_logs 表 (AC: #1, #5)
  - [ ] 1.1 创建 Alembic 迁移：`users` 表添加 `role` 列（VARCHAR(32), NOT NULL, default='trader'）+ `email` 列（可选）
  - [ ] 1.2 创建 Alembic 迁移：`audit_logs` 表（id, user_id, action, resource_type, resource_id, changes_before, changes_after, ip_address, created_at）
  - [ ] 1.3 更新种子数据脚本：默认管理员账户 role='admin'

- [ ] Task 2: 更新 User 模型 + 角色枚举 (AC: #5)
  - [ ] 2.1 定义角色枚举常量：`admin` / `trader` / `storage_operator` / `trading_manager` / `executive_readonly`
  - [ ] 2.2 `app/models/user.py` — 添加 `role: Mapped[str]` 字段（default='trader'）、`email: Mapped[str | None]` 字段
  - [ ] 2.3 `app/models/audit.py` — 创建 AuditLog ORM 模型

- [ ] Task 3: 更新 Pydantic Schemas (AC: #1, #2, #5)
  - [ ] 3.1 `app/schemas/user.py` — 更新 UserRead（添加 role, email, is_locked, created_at, updated_at）、UserCreate（添加 role, email）、UserUpdate（添加 display_name, phone, email, is_active）
  - [ ] 3.2 新建 AdminUserCreate schema（管理员创建用户：username, display_name, phone, email, role）— 不含密码字段（系统生成）
  - [ ] 3.3 新建 AdminResetPasswordResponse schema（返回临时密码）
  - [ ] 3.4 新建 UserListResponse schema（分页：items, total, page, page_size）

- [ ] Task 4: 审计日志 Service (AC: #1, #2, #3, #4, #5)
  - [ ] 4.1 创建 `app/repositories/audit.py` — AuditLogRepository（继承 BaseRepository，添加 get_by_resource / get_by_user 查询方法）
  - [ ] 4.2 创建 `app/services/audit_service.py` — `log_action(user_id, action, resource_type, resource_id, changes_before, changes_after, ip_address)` 异步写入审计记录

- [ ] Task 5: 用户管理 Service 层 (AC: #1, #2, #3, #4, #5)
  - [ ] 5.1 创建 `app/services/user_service.py` — `create_user(admin_user, data)` 生成随机临时密码 + 哈希 + 创建用户 + 写审计日志
  - [ ] 5.2 `update_user(admin_user, user_id, data)` — 更新用户信息 + 记录变更前后值审计日志
  - [ ] 5.3 `reset_password(admin_user, user_id)` — 生成临时密码 + 哈希 + 记录审计日志 + 返回明文临时密码
  - [ ] 5.4 `toggle_active(admin_user, user_id, is_active)` — 停用/启用账户 + 记录审计日志
  - [ ] 5.5 `assign_role(admin_user, user_id, role)` — 角色分配 + 记录变更前后角色审计日志
  - [ ] 5.6 `list_users(page, page_size, search)` — 分页查询用户列表（支持用户名/姓名搜索）
  - [ ] 5.7 `get_user(user_id)` — 获取单个用户详情

- [ ] Task 6: RBAC 权限依赖 (AC: #5)
  - [ ] 6.1 `app/core/dependencies.py` — 添加 `require_roles(allowed_roles: list[str])` 依赖工厂函数
  - [ ] 6.2 更新 JWT Token payload 添加 `role` 字段（create_access_token 增加 role 参数）
  - [ ] 6.3 更新 `get_current_user` 依赖从 Token 中解析 role

- [ ] Task 7: 用户管理 API 端点 (AC: #1, #2, #3, #4, #5)
  - [ ] 7.1 创建 `app/api/v1/users.py` — `GET /api/v1/users` 分页列表（需 admin 角色）
  - [ ] 7.2 `GET /api/v1/users/{user_id}` — 获取用户详情（需 admin 角色）
  - [ ] 7.3 `POST /api/v1/users` — 创建用户（需 admin 角色）→ 返回 UserRead + 临时密码
  - [ ] 7.4 `PUT /api/v1/users/{user_id}` — 更新用户信息（需 admin 角色）
  - [ ] 7.5 `POST /api/v1/users/{user_id}/reset_password` — 重置密码（需 admin 角色）→ 返回临时密码
  - [ ] 7.6 `PUT /api/v1/users/{user_id}/status` — 停用/启用账户（需 admin 角色）
  - [ ] 7.7 `PUT /api/v1/users/{user_id}/role` — 角色分配（需 admin 角色）
  - [ ] 7.8 注册路由到 `app/api/v1/router.py`

- [ ] Task 8: 前端用户管理 API 封装 (AC: #1, #2, #3, #4, #5)
  - [ ] 8.1 创建 `src/api/user.ts` — listUsers, getUser, createUser, updateUser, resetPassword, toggleActive, assignRole

- [ ] Task 9: 前端用户管理 Store (AC: #1, #2)
  - [ ] 9.1 创建 `src/stores/user.ts` — Pinia Store（userList, total, page, pageSize, isLoading, fetchUsers, searchUsers）

- [ ] Task 10: 前端用户管理页面 (AC: #1, #2, #3, #4, #5)
  - [ ] 10.1 创建 `src/views/admin/UserManagementView.vue` — Ant Design Vue Table 用户列表 + 搜索框 + 操作按钮
  - [ ] 10.2 创建用户对话框组件 — Modal + Form（用户名、姓名、联系方式、邮箱、角色选择）
  - [ ] 10.3 编辑用户对话框组件 — 复用创建对话框，预填充数据
  - [ ] 10.4 重置密码确认弹窗 + 显示临时密码对话框
  - [ ] 10.5 停用/启用确认弹窗
  - [ ] 10.6 角色分配下拉选择器 + 确认
  - [ ] 10.7 注册路由 `/admin/users` 到 `src/router/index.ts`（meta: { requiresAuth: true, roles: ['admin'] }）

- [ ] Task 11: 前端路由角色守卫增强 (AC: #5)
  - [ ] 11.1 更新 `src/router/index.ts` — beforeEach 守卫增加 `meta.roles` 校验
  - [ ] 11.2 更新 `src/stores/auth.ts` — UserRead 类型添加 role 字段
  - [ ] 11.3 更新 `src/api/auth.ts` — UserRead interface 添加 role 字段
  - [ ] 11.4 更新 App.vue 侧边栏 — 添加"用户管理"菜单项（仅 admin 角色可见）

- [ ] Task 12: 后端测试 (AC: #1-#5)
  - [ ] 12.1 `tests/unit/services/test_user_service.py` — 创建用户/更新用户/重置密码/停用启用/角色分配/搜索列表
  - [ ] 12.2 `tests/unit/services/test_audit_service.py` — 审计日志写入/查询
  - [ ] 12.3 `tests/unit/repositories/test_audit_repository.py` — 审计日志数据访问
  - [ ] 12.4 `tests/integration/api/test_users.py` — 用户管理 API 端到端测试（含权限校验：非admin调用返回403）

- [ ] Task 13: 前端测试 (AC: #1, #5)
  - [ ] 13.1 `tests/unit/stores/user.test.ts` — user store 状态变更测试
  - [ ] 13.2 `tests/unit/views/UserManagementView.test.ts` — 用户管理页面渲染+交互测试

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
