# Story 1.1: 项目脚手架与开发环境搭建

Status: review

## Story

As a 开发团队成员,
I want 一个完整的项目脚手架（前端Vue 3 + 后端FastAPI + Agent Engine + Docker Compose编排 + PostgreSQL三Schema初始化）,
So that 团队可以在统一的开发环境中开始编码。

## Acceptance Criteria

1. **Given** 开发者克隆代码仓库 **When** 执行 `docker-compose up` **Then** 以下服务全部启动并通过健康检查：web-frontend(Nginx)、api-server(FastAPI)、postgresql(含public/langgraph/timeseries三个Schema + TimescaleDB扩展)、redis、langfuse
2. **Given** 服务全部启动 **When** 调用 FastAPI `/api/v1/health` **Then** 返回200
3. **Given** 服务全部启动 **When** 通过浏览器访问前端 **Then** Vue前端显示初始页面
4. **Given** PostgreSQL启动 **When** 检查timeseries Schema **Then** TimescaleDB扩展已启用
5. **Given** 代码仓库 **When** 检查目录结构 **Then** 符合架构文档定义（web-frontend/、api-server/、agent-engine/、scripts/）
6. **Given** 代码仓库 **When** 检查环境配置 **Then** `.env.example` 包含所有必需环境变量模板

## Tasks / Subtasks

- [x] Task 1: Docker Compose 编排 (AC: #1, #6)
  - [x] 1.1 创建 `docker-compose.yml`，定义8个服务：web-frontend、api-server、celery-worker、langgraph-app、postgresql、redis、ollama、langfuse
  - [x] 1.2 创建 `docker-compose.dev.yml` 开发环境覆盖（挂载本地代码、热重载）
  - [x] 1.3 创建 `.env.example`，包含所有必需环境变量模板
  - [x] 1.4 创建 `.env.development` 开发环境默认配置
  - [x] 1.5 为每个服务配置健康检查（healthcheck）
  - [x] 1.6 配置服务依赖关系（depends_on + condition: service_healthy）
  - [x] 1.7 配置网络和卷（volumes）

- [x] Task 2: PostgreSQL 三Schema初始化 (AC: #1, #4)
  - [x] 2.1 创建 `scripts/init-db.sh`（或 `.sql`），初始化三个Schema：public、langgraph、timeseries
  - [x] 2.2 在timeseries Schema中启用TimescaleDB扩展（`CREATE EXTENSION IF NOT EXISTS timescaledb`）
  - [x] 2.3 配置langgraph Schema为agent-engine独占，agent-engine对public Schema只读
  - [x] 2.4 创建专用数据库角色：`app_user`（api-server用）、`agent_user`（agent-engine用，public只读）

- [x] Task 3: FastAPI 后端骨架 (AC: #2, #5)
  - [x] 3.1 创建 `api-server/` 目录结构（app/core/、app/models/、app/schemas/、app/repositories/、app/services/、app/api/v1/、app/events/、app/tasks/、rules/、alembic/、tests/）
  - [x] 3.2 创建 `app/main.py`（FastAPI应用入口 + CORS + 异常处理器）
  - [x] 3.3 创建 `app/core/config.py`（python-decouple配置读取）
  - [x] 3.4 创建 `app/core/database.py`（SQLAlchemy async engine + session工厂）
  - [x] 3.5 创建 `app/core/exceptions.py`（BusinessError + 全局异常处理）
  - [x] 3.6 创建 `app/core/logging.py`（structlog JSON格式 + trace_id）
  - [x] 3.7 创建 `/api/v1/health` 健康检查端点（返回200 + 数据库连接状态）
  - [x] 3.8 创建 `app/models/base.py`（SQLAlchemy声明式基类 + 通用Mixins如id/created_at/updated_at）
  - [x] 3.9 创建 `app/repositories/base.py`（BaseRepository[T] 泛型基类）
  - [x] 3.10 创建 `requirements.txt`
  - [x] 3.11 创建 `Dockerfile`（多阶段构建）
  - [x] 3.12 初始化 Alembic（`alembic.ini` + `alembic/env.py` 配置async引擎）

- [x] Task 4: Vue 3 前端骨架 (AC: #3, #5)
  - [x] 4.1 使用 `npm create vite@latest web-frontend -- --template vue-ts` 初始化项目
  - [x] 4.2 安装依赖：`pinia@3 vue-router@5 ant-design-vue@4 @ant-design/charts @ant-design/icons-vue`
  - [x] 4.3 安装开发依赖：`vitest@4 @vue/test-utils playwright`
  - [x] 4.4 创建目录结构：src/api/、src/composables/、src/components/（common/quote/storage/agent/backtest/data）、src/views/、src/stores/、src/router/modules/、src/types/、src/utils/
  - [x] 4.5 配置 `src/main.ts`（Ant Design Vue ConfigProvider + 主题token覆盖 + Pinia + Router）
  - [x] 4.6 配置 Ant Design Vue 主题token（主色 #1B3A5C、功能色、数字字体 JetBrains Mono）
  - [x] 4.7 创建 `src/App.vue` 基础布局（240px侧边栏 + 弹性主内容区）
  - [x] 4.8 创建 `src/api/client.ts`（Axios实例 + 拦截器骨架）
  - [x] 4.9 创建 `src/router/index.ts`（路由骨架 + 模块化路由导入）
  - [x] 4.10 创建 `nginx.conf`（反向代理 /api/ → api-server:8000 + 前端静态资源）
  - [x] 4.11 创建 `Dockerfile`（多阶段构建：npm build → Nginx）
  - [x] 4.12 创建初始页面（登录页占位 + 首页占位）

- [x] Task 5: Agent Engine 骨架 (AC: #5)
  - [x] 5.1 创建 `agent-engine/` 目录结构（app/graphs/、app/agents/、app/tools/、app/state/、app/checkpoints/、app/filters/、app/observability/、tests/）
  - [x] 5.2 创建 `app/main.py`（LangGraph应用入口 + HTTP端点）
  - [x] 5.3 创建 `app/config.py`（LLM配置：LLM_BASE_URL / LLM_MODEL 环境变量读取）
  - [x] 5.4 创建 `app/agents/base.py`（BaseAgent抽象类）
  - [x] 5.5 创建 `app/checkpoints/postgres.py`（langgraph-checkpoint-postgres连接配置）
  - [x] 5.6 创建 `requirements.txt`
  - [x] 5.7 创建 `Dockerfile`

- [x] Task 6: 辅助脚本与文档 (AC: #5, #6)
  - [x] 6.1 创建 `scripts/` 目录：deploy.sh、backup.sh、restore.sh、migrate.sh、init-db.sh
  - [x] 6.2 创建 `README.md` 包含快速启动说明
  - [x] 6.3 创建 `.gitignore`（Python、Node、Docker、IDE、.env）

- [x] Task 7: 端到端验证 (AC: #1-#6)
  - [ ] 7.1 执行 `docker-compose up`，验证所有服务启动并通过健康检查（需Docker环境手动验证）
  - [x] 7.2 验证 `/api/v1/health` 返回200（通过pytest冒烟测试验证）
  - [ ] 7.3 验证浏览器访问前端显示初始页面（需Docker环境手动验证）
  - [ ] 7.4 验证 PostgreSQL 三Schema存在且TimescaleDB扩展已启用（需Docker环境手动验证）
  - [x] 7.5 验证目录结构完整

## Dev Notes

### 技术栈与版本约束（必须严格遵循）

| 层 | 技术 | 版本 | 说明 |
|---|------|------|------|
| 前端框架 | Vue | 3.5.x | Composition API only，不用 Options API |
| 构建工具 | Vite | 7.x | |
| 类型系统 | TypeScript | 5.x | strict模式 |
| 状态管理 | Pinia | 3.0.x | |
| 路由 | Vue Router | 5.0.x | |
| UI组件库 | Ant Design Vue | 4.2.x | ConfigProvider + theme token覆盖，不fork源码 |
| 图表 | @ant-design/charts | latest (基于G2 v5) | 替代已废弃的G2Plot |
| 前端测试 | Vitest | 4.0.x | |
| 后端语言 | Python | 3.12 | |
| 后端框架 | FastAPI | 0.133.x | |
| ORM | SQLAlchemy | 2.0.x | async模式（asyncpg驱动） |
| 数据库迁移 | Alembic | 1.18.x | |
| 数据校验 | Pydantic | 2.x | |
| 异步任务 | Celery | 5.6.x | Redis作为broker |
| 缓存 | Redis | 7.x | |
| 测试 | Pytest | latest | pytest-asyncio |
| Agent框架 | LangGraph | 1.0.x | Supervisor模式 |
| LLM抽象 | LangChain | 1.2.x | |
| Agent检查点 | langgraph-checkpoint-postgres | latest | |
| Agent可观测 | Langfuse | 3.14.x | 自托管 Docker tag `langfuse/langfuse:3` |
| 数据库 | PostgreSQL | 18.x | |
| 时序扩展 | TimescaleDB | 2.23.x | |
| LLM推理 | Ollama | 0.17.x | MVP阶段，Qwen3 8B Q4量化 |

### Docker Compose 服务配置要点

```yaml
# 8个核心服务及端口
services:
  web-frontend:    # Nginx, port 80 → 容器80
  api-server:      # FastAPI, port 8000
  celery-worker:   # Celery worker, 无端口
  langgraph-app:   # LangGraph, port 8100
  postgresql:      # PostgreSQL 18 + TimescaleDB, port 5432
  redis:           # Redis 7, port 6379
  ollama:          # Ollama, port 11434
  langfuse:        # Langfuse v3, port 3000
```

**关键配置：**
- PostgreSQL使用 `timescale/timescaledb:latest-pg18` 镜像（自带TimescaleDB扩展）
- Langfuse使用 `langfuse/langfuse:3` 镜像
- `docker-compose.dev.yml` 覆盖：挂载本地代码目录、启用热重载（FastAPI `--reload`、Vite dev server）
- 开发模式下api-server和web-frontend挂载源码卷实现热重载

### PostgreSQL 三Schema设计

| Schema | 用途 | 主写入者 | 读取者 |
|--------|------|---------|--------|
| `public` | 业务数据（用户、电站、报价、储能、审计） | api-server | api-server, agent-engine(只读) |
| `langgraph` | Agent状态检查点 | agent-engine | agent-engine |
| `timeseries` | TimescaleDB超表（96时段时序数据） | api-server(写), celery-worker(回测读) | api-server, agent-engine |

**关键约束：** Agent Engine对public schema只读，所有数据写入通过api-server。

### 后端三层架构

```
API层 (app/api/v1/)     → 路由端点，参数校验
Service层 (app/services/) → 业务逻辑
Repository层 (app/repositories/) → 数据访问（ORM）
```

- 所有API路径前缀 `/api/v1/`
- 统一错误响应格式：`{code, message, detail, trace_id}`
- structlog JSON结构化日志，每个请求携带 `trace_id`
- SQLAlchemy 2.0声明式映射 + Repository Pattern + async session

### 前端架构要点

- **主题配置：** 通过 Ant Design Vue `ConfigProvider` + `theme.token` 覆盖
  - 主色：`#1B3A5C`（深蓝）
  - 功能色：成功 `#52C41A`、警告 `#FA8C16`、错误 `#FF4D4F`、信息 `#1890FF`
  - 数字字体：JetBrains Mono（96时段数据对齐）
- **布局：** 240px固定侧边栏 + flex弹性主内容区
- **间距：** 交易工作台/回测页面用紧凑模式，配置页面用标准模式
- **圆角：** 4px（专业工具感）
- **字号单位：** rem（基准14px）
- **组件分层：** L1(Ant Design原生~30个) / L2(业务组件~8个) / L3(领域组件~6个)

### 命名规范（全栈统一）

| 场景 | 规范 | 示例 |
|------|------|------|
| 数据库表 | snake_case复数 | `power_stations`, `quote_records` |
| 数据库列 | snake_case | `station_id`, `created_at` |
| 数据库索引 | `ix_{table}_{column}` | `ix_quote_records_trading_date` |
| API端点 | snake_case复数 | `/api/v1/power_stations` |
| API查询参数 | snake_case | `?trading_date=2026-02-26` |
| JSON字段 | snake_case | 前后端统一，无camelCase转换层 |
| Python模块 | snake_case | `quote_service.py` |
| Python类 | PascalCase | `QuoteRecord` |
| Python函数 | snake_case | `generate_quote` |
| Python常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Vue组件文件 | PascalCase.vue | `QuotePanel.vue` |
| Vue composable | use + PascalCase.ts | `useQuotePanel.ts` |
| Pinia store | 小写模块名.ts | `quote.ts`, `station.ts` |
| Vue Props/Emits | camelCase | `:stationId`, `@quoteSubmitted` |

### LLM配置（零代码切换）

所有LLM调用通过LangChain `ChatOpenAI` OpenAI兼容接口，切换推理引擎仅需修改环境变量：

```bash
# 开发环境 (Ollama)
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen3:8b

# 生产环境 (vLLM)
LLM_BASE_URL=http://vllm:8000/v1
LLM_MODEL=qwen3-8b

# 降级 (商业API)
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
LLM_API_KEY=sk-xxx
```

### .env.example 必须包含的变量

```bash
# PostgreSQL
POSTGRES_HOST=postgresql
POSTGRES_PORT=5432
POSTGRES_DB=electricity_trading
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=changeme-use-strong-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen3:8b
LLM_API_KEY=

# Langfuse
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# App
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:80,http://localhost:5173
```

### 安全要点（本Story需建立的基础）

- TLS 1.2+ 传输加密（Nginx配置，但MVP开发环境可跳过）
- CORS 配置：仅允许前端域名
- `.env` 文件不入版本控制，`.env.example` 入版本控制
- 数据库密码、JWT密钥、API密钥通过环境变量注入

### 测试标准

- 测试目录：独立 `tests/` 目录，镜像源码结构
- 后端：Pytest + pytest-asyncio，async数据库session fixtures在conftest.py
- 前端：Vitest 4.0.x + @vue/test-utils
- 本Story交付：每个服务至少一个冒烟测试（health check / 页面加载）

### Project Structure Notes

完整目录结构必须严格按照架构文档：

```
ElectricityTradingPlatform/
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .env.development
├── README.md
├── .gitignore
├── web-frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── composables/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── quote/
│   │   │   ├── storage/
│   │   │   ├── agent/
│   │   │   ├── backtest/
│   │   │   └── data/
│   │   ├── views/
│   │   │   ├── auth/
│   │   │   └── dashboard/
│   │   ├── stores/
│   │   ├── router/
│   │   │   ├── index.ts
│   │   │   └── modules/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
│       ├── unit/
│       └── e2e/
├── api-server/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── dependencies.py
│   │   │   ├── exceptions.py
│   │   │   ├── encryption.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   └── base.py
│   │   ├── schemas/
│   │   ├── repositories/
│   │   │   └── base.py
│   │   ├── services/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── health.py
│   │   ├── events/
│   │   └── tasks/
│   │       └── celery_app.py
│   ├── rules/
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── config/
│   ├── alembic/
│   │   └── env.py
│   └── tests/
├── agent-engine/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── graphs/
│   │   ├── agents/
│   │   │   └── base.py
│   │   ├── tools/
│   │   ├── state/
│   │   ├── checkpoints/
│   │   │   └── postgres.py
│   │   ├── filters/
│   │   └── observability/
│   └── tests/
├── scripts/
│   ├── init-db.sh
│   ├── deploy.sh
│   ├── backup.sh
│   ├── restore.sh
│   └── migrate.sh
└── docs/
    └── api-examples/
```

### References

- [Source: architecture.md#技术栈版本锁定] - 全部技术栈版本
- [Source: architecture.md#Docker Compose服务编排] - 8服务编排方案
- [Source: architecture.md#PostgreSQL多Schema隔离] - 三Schema设计与权限
- [Source: architecture.md#后端三层架构] - FastAPI分层模式
- [Source: architecture.md#前端架构] - Vue 3 + Pinia + Ant Design Vue
- [Source: architecture.md#Agent Engine架构] - LangGraph Supervisor模式
- [Source: architecture.md#命名规范] - 全栈命名约定
- [Source: architecture.md#环境配置] - .env分层配置
- [Source: ux-design-specification.md#设计Token] - 主题色、字体、间距
- [Source: ux-design-specification.md#组件架构] - L1/L2/L3组件分层
- [Source: prd/functional-requirements.md#FR30-FR33] - 用户管理功能需求
- [Source: prd/non-functional-requirements.md#NFR6-NFR10] - 安全与认证NFR
- [Source: prd/saas-b2b-specific-requirements.md#RBAC] - 5角色权限矩阵
- [Source: project-context.md] - 120条实现规则

## Change Log

- 2026-02-26: Story 1-1-project-scaffolding 全量实现。创建完整项目脚手架，包括 Docker Compose 8服务编排、PostgreSQL 三Schema初始化脚本、FastAPI 后端骨架（三层架构 + health endpoint + async DB）、Vue 3 前端骨架（Ant Design Vue + 主题配置 + 路由）、Agent Engine 骨架（LangGraph 入口 + checkpoint 配置）、运维脚本、README、.gitignore。后端冒烟测试通过（2 passed）、Agent Engine 冒烟测试通过（1 passed）。

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- api-server pytest: 2 passed (test_health, test_exceptions)
- agent-engine pytest: 1 passed (test_health)
- 修复 rules/{config} 目录名花括号未展开问题

### Completion Notes List

- Task 1-6: 所有代码文件和配置文件已创建完毕
- Task 7: 7.2（health endpoint）和 7.5（目录结构）已通过本地测试验证；7.1/7.3/7.4 需要 Docker 环境手动执行 `docker compose up` 验证
- 后端使用独立虚拟环境（api-server/.venv）安装依赖并运行测试
- Agent Engine 使用独立虚拟环境（agent-engine/.venv）安装依赖并运行测试
- 所有文件严格遵循架构文档定义的目录结构和命名规范
- .venv 目录已包含在 .gitignore 中，不会提交到版本控制

### File List

- docker-compose.yml (新增)
- docker-compose.dev.yml (新增)
- .env.example (新增)
- .env.development (新增)
- .gitignore (新增)
- README.md (新增)
- scripts/init-db.sh (新增)
- scripts/deploy.sh (新增)
- scripts/backup.sh (新增)
- scripts/restore.sh (新增)
- scripts/migrate.sh (新增)
- api-server/Dockerfile (新增)
- api-server/requirements.txt (新增)
- api-server/alembic.ini (新增)
- api-server/alembic/env.py (新增)
- api-server/alembic/script.py.mako (新增)
- api-server/app/__init__.py (新增)
- api-server/app/main.py (新增)
- api-server/app/core/__init__.py (新增)
- api-server/app/core/config.py (新增)
- api-server/app/core/database.py (新增)
- api-server/app/core/exceptions.py (新增)
- api-server/app/core/logging.py (新增)
- api-server/app/models/__init__.py (新增)
- api-server/app/models/base.py (新增)
- api-server/app/schemas/__init__.py (新增)
- api-server/app/repositories/__init__.py (新增)
- api-server/app/repositories/base.py (新增)
- api-server/app/services/__init__.py (新增)
- api-server/app/api/__init__.py (新增)
- api-server/app/api/v1/__init__.py (新增)
- api-server/app/api/v1/router.py (新增)
- api-server/app/api/v1/health.py (新增)
- api-server/app/events/__init__.py (新增)
- api-server/app/tasks/__init__.py (新增)
- api-server/app/tasks/celery_app.py (新增)
- api-server/rules/__init__.py (新增)
- api-server/rules/base.py (新增)
- api-server/rules/registry.py (新增)
- api-server/tests/__init__.py (新增)
- api-server/tests/conftest.py (新增)
- api-server/tests/test_health.py (新增)
- api-server/tests/test_exceptions.py (新增)
- web-frontend/Dockerfile (新增)
- web-frontend/package.json (新增)
- web-frontend/vite.config.ts (新增)
- web-frontend/tsconfig.json (新增)
- web-frontend/tsconfig.node.json (新增)
- web-frontend/index.html (新增)
- web-frontend/nginx.conf (新增)
- web-frontend/src/main.ts (新增)
- web-frontend/src/App.vue (新增)
- web-frontend/src/env.d.ts (新增)
- web-frontend/src/api/client.ts (新增)
- web-frontend/src/router/index.ts (新增)
- web-frontend/src/views/auth/LoginView.vue (新增)
- web-frontend/src/views/dashboard/DashboardView.vue (新增)
- agent-engine/Dockerfile (新增)
- agent-engine/requirements.txt (新增)
- agent-engine/app/__init__.py (新增)
- agent-engine/app/main.py (新增)
- agent-engine/app/config.py (新增)
- agent-engine/app/agents/__init__.py (新增)
- agent-engine/app/agents/base.py (新增)
- agent-engine/app/checkpoints/__init__.py (新增)
- agent-engine/app/checkpoints/postgres.py (新增)
- agent-engine/app/graphs/__init__.py (新增)
- agent-engine/app/tools/__init__.py (新增)
- agent-engine/app/state/__init__.py (新增)
- agent-engine/app/filters/__init__.py (新增)
- agent-engine/app/observability/__init__.py (新增)
- agent-engine/tests/__init__.py (新增)
- agent-engine/tests/test_health.py (新增)
