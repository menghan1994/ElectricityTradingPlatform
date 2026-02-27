---
project_name: 'ElectricityTradingPlatform'
user_name: 'hmeng'
date: '2026-02-26'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 120
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### 前端
- Vue 3.5.x + TypeScript 5.x + Vite 7.x（不使用 Vapor Mode，MVP 不采用 beta 特性）
- Pinia 3.0.x（状态管理）+ Vue Router 5.0.x
- Ant Design Vue 4.2.x + @ant-design/charts（基于 G2 v5，替代已停维的 G2Plot）
- Vitest 4.0.x + Playwright（E2E 测试 + PDF 服务端渲染双用途）

### 后端
- Python 3.12 + FastAPI 0.133.x + Pydantic 2.x
- SQLAlchemy 2.0.x（异步模式，asyncpg 驱动）+ Alembic 1.18.x
- Celery 5.6.x + Redis 7.x（异步任务 + 缓存）

### Agent 引擎
- LangGraph 1.0.x + LangChain 1.2.x + langchain-openai
- langgraph-checkpoint-postgres（状态持久化）
- Langfuse 3.14.x 自托管（Agent 可观测性）

### 数据层
- PostgreSQL 18.x + TimescaleDB 2.23.x（时序数据扩展）
- Redis 7.x（Celery broker + 应用级缓存）

### LLM 部署
- 所有 LLM 调用统一通过 LangChain `ChatOpenAI` 的 OpenAI 兼容接口
- 切换推理引擎仅需修改 `LLM_BASE_URL` + `LLM_MODEL` 配置，零代码改动
- MVP: Ollama 0.17.x + Qwen3 8B → 生产: vLLM + Qwen3 8B → 备选: 国产商业 API
- 不同 Agent 可独立配置不同模型（混合部署）

### 部署
- Docker Compose 单机（MVP）→ Docker Swarm（Phase 2）→ K8s（Phase 3）
- Nginx 反向代理 + TLS 终止 + 前端静态资源
- 本地/私有云部署（数据100%境内，不接受公有云SaaS）

### 关键版本约束
- ⚠️ Vue 3 是硬性要求（国产软件审计合规），不可选 React
- ⚠️ LangGraph v1.0+ 必须使用（MIT 开源，支持完全私有化）
- ⚠️ Langfuse 必须自托管（替代 LangSmith，满足数据本地化）
- ⚠️ Python ≥ 3.12（FastAPI 推荐版本，LangChain 要求 ≥3.10）

### 关键版本差异与常见错误（Agent 必须注意）
- ⚠️ SQLAlchemy 2.0 异步模式：必须用 `AsyncSession` + `async_sessionmaker`，连接字符串 `postgresql+asyncpg://`
- ⚠️ LangGraph 1.0：使用 `StateGraph` API，不是旧版 `MessageGraph`
- ⚠️ LangChain 1.2：导入路径 `from langchain_openai import ChatOpenAI`，不是 `from langchain.chat_models`
- ⚠️ Langfuse 3.14：使用 `@observe` 装饰器，不是手动 `langfuse.trace()` 调用
- ⚠️ 图表库：使用 `@ant-design/charts`，禁止使用已停维的 `@antv/g2plot`
- ⚠️ Pinia 3.0：不需要 `PiniaVuePlugin`，直接 `app.use(createPinia())`
- ⚠️ Vitest 4.0：E2E 通过内置 browser mode 运行，不单独安装 `@playwright/test` runner
- ⚠️ Alembic 异步迁移：`env.py` 需要 `run_async` 包装，不能用同步模板
- ⚠️ TimescaleDB DDL：`create_hypertable()` 和连续聚合必须手写迁移，不能依赖 `--autogenerate`

## Critical Implementation Rules

### Language-Specific Rules

#### Python 规则
- 异步优先：FastAPI 路由函数必须用 `async def`，数据库操作用 `await session.execute()`
- 类型注解：所有函数参数和返回值必须有类型注解（Python 3.12 原生语法，如 `list[str]` 而非 `List[str]`）
- 导入规范：使用 `from __future__ import annotations` 已不再需要（Python 3.12 原生支持）
- Pydantic v2 模型：用 `model_validator` 替代 v1 的 `validator`；用 `model_config = ConfigDict(...)` 替代 `class Config`
- 异常抛出：业务层用 `raise BusinessError(code, message, detail)`，不直接 `raise HTTPException`
- 字符串格式化：使用 f-string，不使用 `.format()` 或 `%` 格式化
- 常量定义：全大写 UPPER_SNAKE_CASE，放在模块顶部或 `core/config.py`
- 环境配置读取：通过 `python-decouple` 的 `config()` 函数，不直接用 `os.environ`

#### TypeScript 规则
- 严格模式：`tsconfig.json` 启用 `strict: true`，禁止 `any` 类型（需要时用 `unknown` + 类型守卫）
- Vue 组件：使用 `<script setup lang="ts">` 语法，不使用 Options API
- Props 定义：用 `defineProps<{ stationId: string }>()` 泛型方式，不用 `defineProps({ stationId: { type: String } })`
- Emits 定义：用 `defineEmits<{ (e: 'quoteSubmitted', id: string): void }>()` 类型声明
- Ref 类型：优先让 TypeScript 自动推断，复杂类型用 `ref<QuoteState | null>(null)`
- 可选链：使用 `?.` 和 `??` 操作符替代手动空值检查
- 枚举：优先使用 `const enum` 或字符串联合类型 `type Role = 'admin' | 'trader'`，避免运行时枚举
- API 返回类型：每个 API 调用函数必须有明确的返回类型，如 `Promise<StationResponse>`

### Framework-Specific Rules

#### Vue 3 规则
- Composition API 专用：所有组件使用 `<script setup lang="ts">`，禁止 Options API
- 组合式函数封装：数据获取 + 状态管理 + 业务逻辑统一封装为 `composables/useXxx.ts`
- 组件内禁止直接调 API：必须通过 `api/` 封装层 + composable 调用，不在组件内写 `axios.get()`
- Pinia Store 结构：按功能模块拆分（quote/storage/agent/station/auth），电站 ID 索引隔离多电站状态
- Store Action 命名：动词开头（`fetchQuotes`、`updatePeriod`、`resetState`）
- Store 间通信：通过 composable 层协调，不直接 Store 互调
- Loading 状态：Store action 内统一管理 `isLoadingXxx`，骨架屏用于首次加载，Spin 用于刷新
- 路由懒加载：`() => import('./views/Quote.vue')`，路由 `meta` 定义权限 `{ roles: ['trader'] }`
- Ant Design Vue 按需导入：通过 `unplugin-vue-components` 自动按需加载
- SSE 连接管理：通过 `composables/useSSE.ts` 统一管理，使用 `EventSource` API（自带断线重连）

#### FastAPI 规则
- 三层架构强制：API 路由层 → Service 层 → Repository 层，业务逻辑禁止写在路由函数中
- 依赖注入：通过 `Depends()` 注入数据库会话、当前用户、权限校验
- RBAC 权限：`Depends(require_roles(['trader', 'admin']))` 装饰器模式
- 统一错误响应：所有错误返回 `{code, message, detail, trace_id}` 结构
- API 版本化：所有端点挂在 `/api/v1/` 前缀下
- RESTful 资源命名：复数名词（`/api/v1/quotes`），禁止动词端点（`/getQuote`）
- 分页响应格式：`{items: [...], total: int, page: int, page_size: int}`
- SSE 推送：用 `StreamingResponse` 实现，事件类型用小写下划线（`agent_progress`）
- structlog 日志：所有日志输出 JSON 格式，包含 `trace_id` 与 Langfuse 链路打通
- Celery 异步任务：回测、PDF 生成、批量数据导入通过 Celery worker 异步执行

#### LangGraph 规则
- 图结构：顶层 Supervisor 编排 → 子图分工（prediction/strategy/storage/risk）
- 状态定义：`TypedDict` 定义 State schema，所有 Agent 共享状态类型
- Human-in-the-Loop：使用 LangGraph 内置 `interrupt()` 机制实现交易员审核中断
- 降级策略：Agent 协作失败 → 自动降级为规则引擎生成报价
- 检查点持久化：`langgraph-checkpoint-postgres` 存储到 `langgraph` Schema
- 可观测性：每个节点集成 Langfuse `@observe`，100% 链路记录
- Token 限制：中间件层强制单次调用 ≤20K Token（NFR29）
- 安全过滤：`filters/input_filter.py` 清洗输入 + `filters/output_filter.py` 校验输出
- Agent 对业务数据只读：决策结果通过 HTTP API 回传 api-server 写入数据库
- 工具函数可测试性：Agent 工具预留依赖注入点和 Mock 接口

### Testing Rules

#### 测试组织
- 测试目录：独立 `tests/` 目录镜像源码结构（非 co-located），三个服务各自独立
- 后端测试结构：`tests/unit/services/`、`tests/unit/repositories/`、`tests/integration/api/`
- 前端测试结构：`tests/unit/composables/`、`tests/unit/stores/`、`tests/e2e/`
- Agent 测试结构：`tests/unit/agents/`、`tests/unit/tools/`、`tests/integration/graphs/`

#### 后端测试规则（Pytest）
- 异步测试：使用 `@pytest.mark.asyncio` + `async def test_xxx()`
- 数据库测试：使用事务回滚隔离（`AsyncSession` fixture），不依赖真实数据
- API 集成测试：使用 `httpx.AsyncClient` + FastAPI `TestClient`，不用 `requests`
- Repository 测试：单元测试 Mock 数据库会话，集成测试用测试数据库
- Service 测试：Mock Repository 依赖，验证业务逻辑
- conftest.py：每个测试目录独立 `conftest.py`，共享 fixture 放顶层

#### 前端测试规则（Vitest）
- 组件测试：使用 `@vue/test-utils` 的 `mount` / `shallowMount`
- Store 测试：使用 `createTestingPinia()` 隔离 Store 状态
- composable 测试：在 `withSetup()` 包装器中测试组合式函数
- API Mock：使用 `vi.mock()` Mock API 模块，不使用 `msw` 等外部库

#### Agent 测试规则（LangGraph 两层策略）
- 单节点单元测试：Mock LLM 响应，验证单个 Agent 节点的输入→输出转换
- 完整图集成测试：使用测试用 LLM（低成本模型），验证端到端图执行流程
- 工具函数测试：通过依赖注入 Mock 外部数据源，验证工具函数逻辑
- 储能约束测试：SOC/倍率边界条件使用属性测试（Hypothesis）覆盖，违反率必须为 0%

#### 通用测试规则
- 测试命名：`test_功能描述_场景_预期结果`（如 `test_generate_quote_missing_data_raises_error`）
- 所有测试必须 100% 通过后才能提交
- 不写无断言的测试，每个测试至少一个有意义的断言
- 测试数据：使用工厂函数/fixture 创建，不硬编码 JSON

### Code Quality & Style Rules

#### 命名规范（全链路统一）
- 数据库表名：snake_case 复数（`power_stations`、`quote_records`）
- 数据库列名：snake_case（`station_id`、`created_at`）
- 外键命名：`{被引用表单数}_id`（`station_id`、`user_id`）
- 索引命名：`ix_{表名}_{列名}`，约束命名：`ck_{表名}_{描述}`
- API 端点：snake_case 复数（`/api/v1/power_stations`）
- API 查询参数：snake_case（`?trading_date=2026-02-26&page_size=20`）
- JSON 字段：前后端统一 snake_case（避免 camelCase ↔ snake_case 转换层）
- Python 文件：snake_case（`quote_service.py`）
- Python 类名：PascalCase（`QuoteRecord`）
- Vue 组件文件：PascalCase.vue（`QuotePanel.vue`）
- Composable 文件：use + PascalCase.ts（`useQuotePanel.ts`）
- Store 文件：小写功能名.ts（`stores/quote.ts`）
- 路由文件：功能名.routes.ts（`quote.routes.ts`）
- 工具函数文件：camelCase.ts（`dateFormat.ts`）
- 组件 Props/Emits：camelCase（`:stationId`、`@quoteSubmitted`）

#### 项目结构规则
- 后端：`app/core/` → `app/models/` → `app/schemas/` → `app/repositories/` → `app/services/` → `app/api/v1/`
- 前端：`src/api/` → `src/composables/` → `src/components/{模块}/` → `src/views/{模块}/` → `src/stores/`
- Agent：`app/graphs/` → `app/agents/` → `app/tools/` → `app/state/` → `app/filters/`
- 省份规则引擎：独立 `rules/` 目录，与 `app/` 平级

#### 数据格式规则
- 日期时间 API 传输：ISO 8601 带时区（`2026-02-26T08:00:00+08:00`）
- 日期时间数据库存储：UTC timestamp with time zone
- 前端展示：转换为北京时间（UTC+8），格式 `YYYY-MM-DD HH:mm`
- 布尔值：`true/false`；空值：使用 `null`，不省略字段
- 96 时段数据：数组 `[{period: 1, price: 0.35}, ...]`，`period` 范围 1-96

### Development Workflow Rules

#### 环境配置
- 多环境文件：`.env.development` / `.env.production`，模板 `.env.example` 提交到 Git
- Docker Compose 开发环境：`docker-compose.dev.yml` 覆盖配置（热重载、调试端口）
- LLM 切换：仅需修改 `.env` 中 `LLM_BASE_URL` 和 `LLM_MODEL`，零代码改动
- 敏感配置（API Key、数据库密码）：禁止提交到 Git，通过 `.env` + `.gitignore` 管理

#### 数据库迁移
- 迁移工具：Alembic，所有 Schema 变更必须通过迁移脚本
- 迁移命名：有意义的描述（`add_quote_records_table`），不用自动生成的哈希名
- TimescaleDB 特殊 DDL（`create_hypertable`、连续聚合）：手写迁移，不依赖 autogenerate
- 多 Schema 隔离：`public`（业务）、`langgraph`（Agent 检查点）、`timeseries`（时序数据）
- 迁移脚本必须可重复执行（幂等），包含 rollback 逻辑

#### Docker Compose 服务
- 8 个核心服务：web-frontend、api-server、celery-worker、langgraph-app、postgresql、redis、ollama、langfuse
- 服务间通信：Docker 内部网络，服务名即主机名（如 `postgresql:5432`）
- 数据持久化：PostgreSQL 和 Redis 数据卷必须映射到宿主机

#### 部署流程（MVP 手动脚本）
- `scripts/deploy.sh`：前端构建 + 数据库迁移 + Docker Compose 部署
- `scripts/backup.sh`：pg_dump 全量备份（每小时，满足 RPO ≤ 1h）
- `scripts/restore.sh`：恢复脚本化（满足 RTO ≤ 4h）
- `scripts/migrate.sh`：Alembic 迁移执行
- `scripts/init-db.sh`：PostgreSQL 三 Schema 初始化 + TimescaleDB 启用

#### 离线/半离线更新
- LLM 模型文件、Agent 配置、前端静态资源、规则引擎插件均需适配无公网环境
- 更新包分发通过离线安装包或内网镜像仓库

### Critical Don't-Miss Rules

#### 反模式清单（禁止出现）
| 反模式 | 正确做法 |
|--------|---------|
| `class users`（表名小写单数） | 模型 PascalCase `class User`，表名 snake_case 复数 `users` |
| `/api/v1/getQuote`（动词端点） | `/api/v1/quotes/{id}`（RESTful 资源） |
| 路由函数里写 SQL 查询 | 通过 Repository 层访问数据 |
| `userId`（API JSON camelCase） | `user_id`（统一 snake_case） |
| 组件内直接 `axios.get(...)` | 通过 `api/quote.ts` 封装 + composable 调用 |
| `loading = true` 散落在各处 | Store action 内统一管理 `isLoadingQuotes` |
| `from langchain.chat_models import ChatOpenAI` | `from langchain_openai import ChatOpenAI` |
| `sessionmaker` 同步会话 | `async_sessionmaker` + `AsyncSession` |
| `@antv/g2plot` 图表导入 | `@ant-design/charts` |
| `raise HTTPException` 在 Service 层 | `raise BusinessError(code, message, detail)` |

#### 三层降级策略（必须实现）
- Agent 协作失败 → 规则引擎生成报价（用户无感切换）
- 储能引擎异常 → 无储能模式报价（仅发电侧报价）
- 外部数据源异常 → 缓存数据（30秒自动切换，缓存有效期 ≤24h）

#### 安全规则
- Prompt 注入防护：Agent 输入输出安全过滤层（`filters/`），清洗敏感信息和注入模式
- 传输加密：Nginx TLS 1.2+ 终止
- 存储加密：敏感字段（API Key、LLM 密钥）AES-256 加密，SQLAlchemy `TypeDecorator` 封装
- 密码存储：bcrypt 哈希（不可逆），禁止明文存储
- CORS 白名单：仅允许前端域名
- Rate Limiting：Redis 令牌桶防暴力攻击
- 审计日志：追加写入模式，不可修改/删除，保留 ≥3年

#### 储能设备安全约束（违反率必须为 0%）
- SOC 上下限硬校验：充放电指令超出 SOC 安全范围自动拦截
- 充放电倍率校验：超出设备额定倍率的指令自动拦截
- 属性测试/模糊测试必须覆盖所有边界条件

#### 错误处理分层
- 前端 API 层（Axios 拦截器）：401→跳转登录、403→权限不足、500→通用错误+trace_id
- 后端 Service 层：业务异常 `BusinessError`、校验异常 Pydantic `ValidationError`（422）、系统异常全局 `ExceptionHandler`
- Agent 层：执行异常→降级规则引擎、LLM 超时→重试1次→降级备选模型→降级规则引擎、Token 超限→截断+告警

#### 重试策略
- LLM 调用：最多重试 1 次，间隔 2 秒
- 外部数据源 API：最多重试 2 次，指数退避（1s → 2s）
- 数据库操作：不重试，直接报错
- 前端 API 调用：网络错误重试 1 次，业务错误不重试

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-02-26
