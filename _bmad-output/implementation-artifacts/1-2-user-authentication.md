# Story 1.2: 用户认证（登录/登出/会话管理）

Status: done

## Story

As a 系统用户,
I want 通过用户名和密码安全登录系统，并在无操作30分钟后自动登出,
So that 我的账户和数据安全受到保护。

## Acceptance Criteria

1. **Given** 数据库中存在已创建的用户账户 **When** 用户输入正确的用户名和密码并提交登录 **Then** 系统返回Access Token（30分钟有效期）和Refresh Token（7天，httpOnly Cookie存储），用户被重定向到首页

2. **Given** 用户已登录 **When** 30分钟内无任何操作 **Then** 会话自动过期，用户被重定向到登录页

3. **Given** 用户连续5次输入错误密码 **When** 第5次登录失败 **Then** 账户被锁定15分钟，期间无法登录，并提示锁定剩余时间

4. **Given** 用户已登录 **When** 用户点击登出 **Then** Access Token失效、Refresh Token Cookie被清除、用户被重定向到登录页

5. **Given** 用户输入的密码不满足强密码策略（<8位或缺少大小写/数字/特殊字符） **When** 注册或修改密码时 **Then** 系统拒绝并提示具体的密码要求

## Tasks / Subtasks

- [x] Task 1: 用户数据模型与数据库迁移 (AC: #1, #3)
  - [x] 1.1 创建 `app/models/user.py` — User 模型（id, username, hashed_password, display_name, phone, is_active, is_locked, locked_until, failed_login_attempts, last_login_at, created_at, updated_at）
  - [x] 1.2 创建 Alembic 迁移脚本 — `create_users_table`，含唯一索引 `ix_users_username`
  - [x] 1.3 创建种子数据脚本 — 默认管理员账户（admin/初始密码），用于系统初始化

- [x] Task 2: 安全核心模块 (AC: #1, #5)
  - [x] 2.1 创建 `app/core/security.py` — bcrypt 密码哈希（hash_password/verify_password）+ PyJWT Token 生成/验证（create_access_token/create_refresh_token/decode_token）
  - [x] 2.2 密码强度校验函数 — ≥8位，必须包含大小写字母+数字+特殊字符
  - [x] 2.3 创建 `app/core/dependencies.py` — `get_current_user` 依赖（从 Bearer Token 解析用户）、`get_current_active_user` 依赖（校验账户未停用/未锁定）

- [x] Task 3: 认证 Pydantic Schemas (AC: #1, #3, #4, #5)
  - [x] 3.1 创建 `app/schemas/auth.py` — LoginRequest, TokenResponse, RefreshResponse
  - [x] 3.2 创建 `app/schemas/user.py` — UserCreate, UserRead, UserUpdate, ChangePasswordRequest

- [x] Task 4: 用户 Repository 层 (AC: #1, #3)
  - [x] 4.1 创建 `app/repositories/user.py` — UserRepository（继承 BaseRepository），含 `get_by_username`、`increment_failed_attempts`、`reset_failed_attempts`、`lock_account`、`update_last_login` 方法

- [x] Task 5: 认证 Service 层 (AC: #1, #2, #3, #4, #5)
  - [x] 5.1 创建 `app/services/auth_service.py` — `authenticate`（校验凭据+检查锁定+生成Token）、`refresh_access_token`（从 Refresh Token 换取新 Access Token）、`logout`（清除 Cookie）
  - [x] 5.2 实现账户锁定逻辑 — 连续5次失败锁定15分钟，成功登录重置计数器
  - [x] 5.3 密码修改接口 — 验证旧密码 + 校验新密码强度 + 更新哈希

- [x] Task 6: 认证 API 端点 (AC: #1, #2, #3, #4)
  - [x] 6.1 创建 `app/api/v1/auth.py` — `POST /api/v1/auth/login`（返回 Access Token + 设置 httpOnly Refresh Token Cookie）
  - [x] 6.2 `POST /api/v1/auth/refresh` — 从 Cookie 读取 Refresh Token，返回新 Access Token
  - [x] 6.3 `POST /api/v1/auth/logout` — 清除 Refresh Token Cookie
  - [x] 6.4 `POST /api/v1/auth/change_password` — 修改密码（需已认证）
  - [x] 6.5 `GET /api/v1/auth/me` — 返回当前用户信息
  - [x] 6.6 注册路由到 `app/api/v1/router.py`

- [x] Task 7: 前端认证状态管理 (AC: #1, #2, #4)
  - [x] 7.1 创建 `src/stores/auth.ts` — Pinia Store（accessToken, user, isAuthenticated, login/logout/refreshToken actions）
  - [x] 7.2 创建 `src/api/auth.ts` — API 封装（login, refreshToken, logout, getMe, changePassword）
  - [x] 7.3 创建 `src/composables/useAuth.ts` — 认证组合式函数（登录/登出逻辑 + 权限校验）

- [x] Task 8: 前端登录页实现 (AC: #1, #3, #5)
  - [x] 8.1 完善 `src/views/auth/LoginView.vue` — Ant Design Vue Form 双向绑定、表单校验（必填+密码最低8位）、错误提示（凭据错误/账户锁定+剩余时间）、loading 状态
  - [x] 8.2 登录成功后保存 Token 到 localStorage + 跳转首页

- [x] Task 9: 前端路由守卫与 Token 刷新 (AC: #2, #4)
  - [x] 9.1 实现 `router/index.ts` 路由守卫 — 未认证用户重定向到 `/login`，已认证用户跳过登录页
  - [x] 9.2 完善 `src/api/client.ts` — 拦截器添加 Access Token 过期自动调用 `/auth/refresh` 刷新逻辑（静默续签）
  - [x] 9.3 实现前端30分钟无操作自动登出 — 监听用户交互事件，30分钟无操作清除 Token 跳转登录页

- [x] Task 10: 后端测试 (AC: #1-#5)
  - [x] 10.1 `tests/unit/services/test_auth_service.py` — 正常登录/错误密码/账户锁定/锁定过期解锁/密码修改/密码强度校验
  - [x] 10.2 `tests/integration/api/test_auth.py` — 登录 API/刷新 Token/登出/修改密码端到端测试
  - [x] 10.3 `tests/unit/repositories/test_user_repository.py` — 用户查询/创建/锁定操作

- [x] Task 11: 前端测试 (AC: #1, #3)
  - [x] 11.1 `tests/unit/stores/auth.test.ts` — auth store 状态变更测试
  - [x] 11.2 `tests/unit/composables/useAuth.test.ts` — 认证逻辑测试

## Dev Notes

### 技术选型（已验证 2026-02）

| 库 | 版本 | 说明 |
|---|------|------|
| **PyJWT** | 2.11.0 | JWT Token 生成/验证。**禁止使用 python-jose**（已废弃，3年无更新） |
| **bcrypt** | 5.0.0 | 密码哈希。**直接使用 bcrypt，禁止使用 passlib**（与 bcrypt 5.0.0 不兼容） |
| OAuth2PasswordBearer | FastAPI 内置 | Token 提取机制，`tokenUrl="auth/login"` |

**关键版本注意事项：**
- bcrypt 5.0.0 对超过72字节的密码会抛出 `ValueError`（安全改进），需在校验层提前截断或提示
- PyJWT 导入路径：`import jwt`，不是 `import jose`
- FastAPI 0.133.x 启用了严格 Content-Type 检查，登录请求 body 必须是 JSON

### 现有代码基础（Story 1.1 已建立）

**可直接复用：**
- `app/core/config.py` — 已有 `JWT_SECRET_KEY`、`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`、`JWT_REFRESH_TOKEN_EXPIRE_DAYS` 配置
- `app/core/database.py` — AsyncSession + async_sessionmaker 已就绪
- `app/core/exceptions.py` — BusinessError 异常类已定义
- `app/core/logging.py` — structlog + TraceIdMiddleware 已配置
- `app/models/base.py` — IdMixin（UUID主键）+ TimestampMixin（created_at/updated_at）已定义
- `app/repositories/base.py` — BaseRepository[T] 泛型基类已实现（get_by_id/get_all/create/delete）
- `app/main.py` — CORSMiddleware + TraceIdMiddleware + 全局异常处理器已注册
- `web-frontend/src/api/client.ts` — Axios 实例已创建，请求拦截器已添加 Bearer Token 从 localStorage 读取，401 响应拦截器已处理跳转登录
- `web-frontend/src/router/index.ts` — `/login` 路由已定义（`meta: { requiresAuth: false }`），`/` 首页已定义（`meta: { requiresAuth: true }`）
- `web-frontend/src/views/auth/LoginView.vue` — 占位 UI 已有（用户名/密码输入框 + 登录按钮，400px Card）

**需要新建的文件：**
- `app/core/security.py` — 密码哈希 + JWT Token 工具
- `app/core/dependencies.py` — FastAPI 认证依赖
- `app/models/user.py` — User ORM 模型
- `app/schemas/auth.py` — 认证相关 Pydantic Schema
- `app/schemas/user.py` — 用户相关 Pydantic Schema
- `app/repositories/user.py` — 用户 Repository
- `app/services/auth_service.py` — 认证 Service
- `app/api/v1/auth.py` — 认证 API 端点
- `alembic/versions/xxxx_create_users_table.py` — 数据库迁移
- `web-frontend/src/stores/auth.ts` — 认证 Pinia Store
- `web-frontend/src/api/auth.ts` — 认证 API 封装
- `web-frontend/src/composables/useAuth.ts` — 认证组合式函数

### 架构合规要求

**三层架构（强制）：**
```
API 层 (app/api/v1/auth.py)
  → 路由端点，参数校验，设置 Cookie
  → 禁止在此层写业务逻辑

Service 层 (app/services/auth_service.py)
  → 认证逻辑、锁定逻辑、Token 生成
  → 使用 BusinessError 抛出业务异常

Repository 层 (app/repositories/user.py)
  → 数据库操作：查询/创建/更新用户
  → 继承 BaseRepository[User]
```

**API 端点设计：**
```
POST /api/v1/auth/login          → LoginRequest body → TokenResponse + Set-Cookie
POST /api/v1/auth/refresh        → Cookie 中的 refresh_token → TokenResponse
POST /api/v1/auth/logout         → Delete-Cookie
POST /api/v1/auth/change_password → ChangePasswordRequest body → 200 OK
GET  /api/v1/auth/me             → UserRead（需 Bearer Token）
```

**错误响应格式（统一）：**
```json
{
  "code": "INVALID_CREDENTIALS",
  "message": "用户名或密码错误",
  "detail": null,
  "trace_id": "abc-123"
}
```

**认证错误码定义：**
| 错误码 | HTTP Status | 含义 |
|--------|-------------|------|
| `INVALID_CREDENTIALS` | 401 | 用户名或密码错误（不泄露具体是哪个） |
| `ACCOUNT_LOCKED` | 403 | 账户被锁定，detail 含 `remaining_minutes` |
| `ACCOUNT_DISABLED` | 403 | 账户已停用 |
| `TOKEN_EXPIRED` | 401 | Token 已过期 |
| `TOKEN_INVALID` | 401 | Token 格式错误或签名无效 |
| `REFRESH_TOKEN_MISSING` | 401 | Cookie 中无 Refresh Token |
| `PASSWORD_TOO_WEAK` | 422 | 密码不满足强度要求，detail 含具体规则 |
| `PASSWORD_MISMATCH` | 400 | 旧密码不匹配 |

### JWT Token 设计

**Access Token（短期）：**
```python
payload = {
    "sub": str(user.id),       # UUID 字符串
    "username": user.username,
    "role": user.role,         # Story 1.3 添加角色后使用
    "exp": now + 30min,
    "iat": now,
    "type": "access"
}
# 算法: HS256
# 存储: 前端 localStorage（通过 API 响应体返回）
```

**Refresh Token（长期）：**
```python
payload = {
    "sub": str(user.id),
    "exp": now + 7days,
    "iat": now,
    "type": "refresh"
}
# 算法: HS256
# 存储: httpOnly Cookie
# Cookie 参数:
#   key="refresh_token"
#   httponly=True
#   secure=True（生产环境，开发环境可设为 False）
#   samesite="lax"
#   path="/api/v1/auth"（限制 Cookie 作用域到认证端点）
#   max_age=604800（7天秒数）
```

### 账户锁定机制

```
登录流程:
1. 查询用户 → 不存在 → 返回 INVALID_CREDENTIALS
2. 检查 is_locked + locked_until → 已锁定且未过期 → 返回 ACCOUNT_LOCKED + remaining_minutes
3. 检查 is_locked + locked_until → 已锁定但已过期 → 自动解锁（重置 is_locked/failed_login_attempts/locked_until）
4. 验证密码 → 错误 → failed_login_attempts += 1
   → 如果 failed_login_attempts >= 5 → is_locked=True, locked_until=now+15min
   → 返回 INVALID_CREDENTIALS（不泄露剩余尝试次数）
5. 验证密码 → 正确 → 重置 failed_login_attempts=0 → 生成 Token → 返回
```

### 密码策略

```python
# 强密码规则：
# - 最少 8 个字符
# - 至少 1 个大写字母 [A-Z]
# - 至少 1 个小写字母 [a-z]
# - 至少 1 个数字 [0-9]
# - 至少 1 个特殊字符 [!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~]
# - 最多 72 字节（bcrypt 5.0.0 限制）

PASSWORD_RULES_ZH = [
    "密码长度至少8个字符",
    "必须包含至少1个大写字母",
    "必须包含至少1个小写字母",
    "必须包含至少1个数字",
    "必须包含至少1个特殊字符（如 !@#$%^&*）",
]
```

### 前端实现要点

**Auth Store（Pinia）：**
```typescript
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserRead | null>(null)
  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username: string, password: string) { ... }
  async function logout() { ... }
  async function refreshToken() { ... }  // 静默刷新
  async function fetchMe() { ... }       // 获取当前用户信息
  function clearAuth() { ... }           // 清除本地状态
})
```

**路由守卫：**
```typescript
// router/index.ts — beforeEach 守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})
```

**30分钟无操作自动登出：**
```typescript
// composables/useAuth.ts 或 App.vue
// 监听 mousemove, keydown, click, scroll 事件
// 每次交互重置 30 分钟定时器
// 定时器到期 → 调用 logout() → 跳转 /login
// 注意：Access Token 本身30分钟过期可作为服务端保障
//       前端定时器作为用户体验优化（提前提示 + 跳转）
```

**Axios Token 自动刷新（401 拦截器）：**
```typescript
// api/client.ts — 响应拦截器增强
// 收到 401 且 code === 'TOKEN_EXPIRED'
// → 调用 /api/v1/auth/refresh（Cookie 自动携带 refresh_token）
// → 成功 → 更新 access_token + 重试原请求
// → 失败 → 清除认证状态 + 跳转登录页
// 注意：需要防止并发请求同时触发多次 refresh
```

**LoginView 错误展示：**
- 凭据错误 → Alert warning "用户名或密码错误"
- 账户锁定 → Alert error "账户已锁定，剩余 X 分钟"
- 网络错误 → Alert error "网络连接失败，请检查网络"

### 数据库设计

**users 表（public Schema）：**

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, default uuid4 | IdMixin |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| hashed_password | VARCHAR(128) | NOT NULL | bcrypt 哈希 |
| display_name | VARCHAR(64) | | 显示名称 |
| phone | VARCHAR(20) | | 联系电话 |
| is_active | BOOLEAN | NOT NULL, default TRUE | 账户启用状态 |
| is_locked | BOOLEAN | NOT NULL, default FALSE | 锁定状态 |
| locked_until | TIMESTAMP WITH TZ | | 锁定截止时间 |
| failed_login_attempts | INTEGER | NOT NULL, default 0 | 连续失败次数 |
| last_login_at | TIMESTAMP WITH TZ | | 最后登录时间 |
| created_at | TIMESTAMP WITH TZ | NOT NULL, server_default now() | TimestampMixin |
| updated_at | TIMESTAMP WITH TZ | NOT NULL, auto update | TimestampMixin |

**注意：** `role` 字段将在 Story 1.3（用户管理与角色分配）中添加，本 Story 暂不包含角色系统。

### 安全注意事项

1. **不泄露用户是否存在**：登录失败统一返回 `INVALID_CREDENTIALS`，不区分"用户不存在"和"密码错误"
2. **密码哈希 rounds=14**：bcrypt gensalt rounds 设为14（约1秒哈希时间，防暴力破解）
3. **Refresh Token Cookie path 限制**：`path="/api/v1/auth"` 限制 Cookie 仅在认证端点发送，减少暴露面
4. **开发环境 Cookie secure=False**：开发环境无 HTTPS，需根据 `APP_ENV` 判断设置 `secure` 参数
5. **并发 Token 刷新防护**：前端需用 Promise 锁防止多个401同时触发 refresh
6. **审计日志预留**：登录/登出/密码修改操作需记录审计日志，但审计模型将在 Story 1.3 中实现。本 Story 先用 structlog 记录关键操作日志

### 与后续 Story 的关系

- **Story 1.3（用户管理与角色分配）**：将添加 `role` 字段到 users 表、用户 CRUD API、角色分配，本 Story 的 User 模型需预留扩展空间
- **Story 1.4（电站绑定）**：基于 RBAC 的数据过滤，依赖本 Story 的认证基础
- **Story 1.5（数据访问控制）**：行级数据过滤，依赖本 Story 的 `get_current_user` 依赖注入

### Project Structure Notes

- 所有新文件位于 Story 1.1 已创建的目录结构中，无需新建目录
- 后端代码路径：`api-server/app/` 下各子目录
- 前端代码路径：`web-frontend/src/` 下各子目录
- 测试路径：各服务 `tests/` 目录下

### References

- [Source: architecture.md#Authentication & Security] — JWT 双 Token 设计、RBAC 权限模型、密码策略
- [Source: architecture.md#API & Communication Patterns] — RESTful 端点设计、错误响应格式
- [Source: architecture.md#Implementation Patterns] — 三层架构、命名规范、反模式清单
- [Source: epics/epic-1.md#Story 1.2] — 原始需求和验收标准
- [Source: prd/non-functional-requirements.md#NFR8] — 密码策略/会话超时/账户锁定
- [Source: prd/non-functional-requirements.md#NFR6] — TLS 1.2+ 传输加密
- [Source: project-context.md#Critical Implementation Rules] — 反模式清单、安全规则
- [Source: 1-1-project-scaffolding.md] — 已建立的代码基础和文件清单

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- 修复 `test_login_triggers_lock_on_max_failures` 测试：Mock 的 `increment_failed_attempts` 需要 side_effect 来模拟计数器递增
- 修复集成测试 DB 连接问题：从 `patch` 改为 `app.dependency_overrides` 注入 mock service
- 添加 `jsdom` 依赖到前端 devDependencies + 配置 vitest `environment: 'jsdom'`
- 修复 `app.test.ts` 断言：侧边栏现在只在已认证时显示，将断言改为检查 header 文字

### Completion Notes List

- 后端完整实现三层架构：API → Service → Repository，所有业务逻辑在 Service 层
- 使用 bcrypt 5.0.0（rounds=14）进行密码哈希，PyJWT 2.11.0 处理 JWT
- JWT 双 Token 设计：Access Token 通过 API body 返回，Refresh Token 通过 httpOnly Cookie
- 账户锁定机制：5次失败锁定15分钟，登录成功重置，过期自动解锁
- 密码强度校验：≥8字符 + 大写 + 小写 + 数字 + 特殊字符 + ≤72字节
- 前端 Pinia Store + Axios 拦截器实现 Token 自动刷新（含并发锁）
- 前端 30 分钟无操作自动登出（useAuth composable）
- 登录页完整实现：表单校验、错误提示（凭据错误/账户锁定/网络错误）、loading 状态
- App.vue 侧边栏条件渲染（仅认证后显示）+ header 登出按钮
- 所有错误码按 story 规范定义（INVALID_CREDENTIALS、ACCOUNT_LOCKED 等）
- 安全措施：不泄露用户是否存在、Cookie path 限制、开发环境 secure=False
- 测试结果：后端 38/38 通过（含原有测试），前端 14/14 通过（含原有测试）

### File List

**新建文件：**
- api-server/app/models/user.py — User ORM 模型
- api-server/app/core/security.py — 密码哈希 + JWT Token 工具
- api-server/app/core/dependencies.py — FastAPI 认证依赖注入
- api-server/app/schemas/auth.py — 认证请求/响应 Schema
- api-server/app/schemas/user.py — 用户读写 Schema
- api-server/app/repositories/user.py — 用户 Repository
- api-server/app/services/auth_service.py — 认证 Service
- api-server/app/api/v1/auth.py — 认证 API 端点
- api-server/alembic/versions/001_create_users_table.py — users 表迁移
- api-server/scripts/seed_admin.py — 管理员种子数据脚本
- api-server/tests/unit/services/test_auth_service.py — AuthService 单元测试（19 tests）
- api-server/tests/unit/repositories/test_user_repository.py — UserRepository 单元测试（7 tests）
- api-server/tests/integration/api/test_auth.py — 认证 API 集成测试（9 tests）
- web-frontend/src/stores/auth.ts — 认证 Pinia Store
- web-frontend/src/api/auth.ts — 认证 API 封装
- web-frontend/src/composables/useAuth.ts — 认证组合式函数（含30分钟无操作登出）
- web-frontend/tests/unit/stores/auth.test.ts — auth store 测试（9 tests）
- web-frontend/tests/unit/composables/useAuth.test.ts — useAuth composable 测试（4 tests）

**修改文件：**
- api-server/requirements.txt — 添加 bcrypt==5.0.0, PyJWT==2.11.0
- api-server/alembic/env.py — 导入 User 模型
- api-server/app/api/v1/router.py — 注册 auth 路由
- web-frontend/src/views/auth/LoginView.vue — 完善登录表单（v-model、校验、错误提示）
- web-frontend/src/router/index.ts — 添加 beforeEach 路由守卫
- web-frontend/src/api/client.ts — 增强 401 拦截器（Token 自动刷新 + 并发锁）
- web-frontend/src/App.vue — 条件侧边栏 + 登出按钮 + useAuth 集成
- web-frontend/vite.config.ts — 添加 test.environment: 'jsdom'
- web-frontend/tests/unit/app.test.ts — 更新断言（适配条件侧边栏）
- web-frontend/package.json — 添加 jsdom devDependency
- docker-compose.dev.yml — api-server 启动命令添加 pip install

**自动生成文件（工具产物）：**
- web-frontend/components.d.ts — unplugin-vue-components 自动生成
- web-frontend/package-lock.json — npm 锁文件

## Change Log

- 2026-02-27: 实现 Story 1.2 用户认证全部 11 个 Task — 后端三层架构 + JWT 双 Token + 账户锁定 + 密码策略 + 前端登录/登出/Token 刷新 + 52 个测试全部通过
- 2026-02-27: [Code Review] 修复 4 个 HIGH + 4 个 MEDIUM 问题 — bcrypt 72字节防护、verify_password 异常处理、Token 刷新无限循环防护（独立 axios 实例）、logout 端点添加认证守卫、useAuth watch 认证状态变化、集成测试文档说明、File List 补全
