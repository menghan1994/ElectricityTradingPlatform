# Story 3.1: 功率预测模型配置与监控

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 系统管理员（老周）,
I want 配置功率预测模型的接入参数并监控其运行状态,
so that 预测模型能正常为交易员提供预测数据，异常时我能及时发现。

## Acceptance Criteria

1. **AC1 - 模型配置管理**: Given 管理员已登录并进入预测模型配置页面 | When 管理员填写模型接入参数（API端点、认证密钥、调用频率、超时时间）并保存 | Then 模型配置保存成功，系统尝试连接验证并显示连接状态
2. **AC2 - 模型运行状态监控**: Given 已配置的预测模型 | When 管理员查看模型管理页面 | Then 展示每个模型的运行状态（运行中/异常/已停用）
3. **AC3 - 异常自动检测与告警**: Given 预测模型API调用失败或超时 | When 系统检测到异常 | Then 模型状态自动更新为"异常"，系统在5分钟内发出告警通知并记录失败原因
4. **AC4 - 可扩展适配器架构**: Given 功率预测模型接口设计 | When 需要接入新的预测模型 | Then 仅需配置适配器参数，不需修改核心代码，新模型接入工作量≤1人天

## Tasks / Subtasks

### 后端任务

- [x] Task 1: 数据库迁移 - 新增预测模型配置表和预测数据表 (AC: #1, #2, #3)
  - [x]1.1 创建 `public.prediction_models` 表：id(UUID), station_id(FK→power_stations), model_name, model_type(enum: wind/solar/hybrid), api_endpoint, api_key_encrypted(BYTEA, AES-256), api_auth_type(api_key/bearer/none), call_frequency_cron(cron表达式), timeout_seconds(int, default 30), is_active(boolean), status(enum: running/error/disabled), last_check_at(timestamptz), last_check_status(varchar), last_check_error(text), created_at, updated_at
  - [x]1.2 创建 `timeseries.power_predictions` 表（TimescaleDB hypertable，按 prediction_date 分区）：id(UUID), prediction_date(date, 分区键), period(int 1-96), station_id(FK→power_stations), model_id(FK→prediction_models), predicted_power_kw(decimal(12,2)), confidence_upper_kw(decimal(12,2)), confidence_lower_kw(decimal(12,2)), source(api/manual), fetched_at(timestamptz), created_at(timestamptz)
  - [x]1.3 添加索引：(station_id, prediction_date) 复合索引、(station_id, prediction_date, period, model_id) 唯一约束
  - [x]1.4 迁移脚本编号 011，使用 `if_not_exists` 保护 create_hypertable，TimescaleDB DDL 手写

- [x]Task 2: Model层 - 新增 SQLAlchemy ORM 模型 (AC: #1, #2)
  - [x]2.1 新增 `app/models/prediction.py`：`PredictionModel` 模型（public schema），api_key_encrypted 使用 EncryptedType（cryptography.Fernet AES 加密，与 Story 2.6 市场数据源一致）
  - [x]2.2 新增 `PowerPrediction` 模型（timeseries schema hypertable，复合主键 id+prediction_date）
  - [x]2.3 在 `models/__init__.py` 中注册新模型

- [x]Task 3: Schema层 - 新增 Pydantic 请求/响应模型 (AC: #1, #2, #3)
  - [x]3.1 新增 `app/schemas/prediction.py`
  - [x]3.2 `PredictionModelCreate` schema：model_name, model_type, api_endpoint, api_key(明文输入), api_auth_type, call_frequency_cron, timeout_seconds, station_id
  - [x]3.3 `PredictionModelUpdate` schema：部分字段可选更新
  - [x]3.4 `PredictionModelRead` schema：api_key 脱敏显示（仅显示后4位），包含 status, last_check_at, last_check_status
  - [x]3.5 `PredictionModelStatus` schema：model_id, model_name, station_name, status(running/error/disabled), last_check_at, last_check_error, uptime_percentage(可选)
  - [x]3.6 `ConnectionTestResult` schema：success(bool), latency_ms(float), error_message(optional), tested_at

- [x]Task 4: Repository层 - 新增数据访问方法 (AC: #1, #2, #3)
  - [x]4.1 新增 `app/repositories/prediction.py`：`PredictionModelRepository`
  - [x]4.2 方法：create, update, delete, get_by_id, get_by_station_id, get_all_active, update_status, update_check_result
  - [x]4.3 新增 `PowerPredictionRepository`：bulk_upsert, get_by_station_date_model, get_latest_by_station

- [x]Task 5: Service层 - 预测模型配置与监控业务逻辑 (AC: #1, #2, #3, #4)
  - [x]5.1 新增 `app/services/prediction_service.py`：`PredictionService` 类
  - [x]5.2 实现 CRUD 操作（create_model, update_model, delete_model, get_model, list_models）
  - [x]5.3 实现 `test_connection(model_id)` - 异步调用预测模型 API 验证连通性，返回延迟和状态
  - [x]5.4 实现 `check_model_health(model_id)` - 健康检查，更新模型状态（running/error）
  - [x]5.5 实现 `get_all_model_statuses()` - 获取所有模型运行状态概览
  - [x]5.6 所有操作写入审计日志（audit_service.log）
  - [x]5.7 模型创建时自动执行一次连接测试

- [x]Task 6: 预测模型适配器 - 可扩展接口设计 (AC: #4)
  - [x]6.1 创建 `app/services/prediction_adapters/base.py`：`BasePredictionAdapter` 抽象基类
    - `async fetch_predictions(station_id, prediction_date) -> list[PredictionRecord]`
    - `async health_check() -> bool`
    - `get_adapter_info() -> dict` （返回适配器名称、版本、支持的模型类型）
  - [x]6.2 创建 `app/services/prediction_adapters/generic.py`：`GenericPredictionAdapter` 通用适配器
    - 支持标准 JSON API 格式（与市场数据适配器架构一致）
    - httpx.AsyncClient 异步调用，超时可配置
    - 重试逻辑：最多2次，指数退避（1s→2s）
    - 响应解析：期望 JSON 数组，每项含 period, predicted_power_kw, confidence_upper_kw, confidence_lower_kw
  - [x]6.3 创建 `app/services/prediction_adapters/__init__.py`：工厂方法 `get_adapter(model_config) -> BasePredictionAdapter`

- [x]Task 7: Celery 定时任务 - 模型健康检查 (AC: #3)
  - [x]7.1 新增 `app/tasks/prediction_tasks.py`
  - [x]7.2 实现 `check_prediction_models_health()` Celery 定时任务：每5分钟执行一次
  - [x]7.3 遍历所有 active 模型 → 调用适配器 health_check → 更新状态
  - [x]7.4 状态变更为 error 时：structlog WARNING 告警 + 记录失败原因
  - [x]7.5 在 celery_app.py 中注册任务模块 + beat schedule

- [x]Task 8: API层 - 预测模型管理端点 (AC: #1, #2, #3, #4)
  - [x]8.1 新增 `app/api/v1/predictions.py` 路由模块
  - [x]8.2 `GET /api/v1/prediction-models` - 列出所有预测模型（支持 station_id 过滤）
  - [x]8.3 `POST /api/v1/prediction-models` - 新建预测模型配置（admin only）
  - [x]8.4 `PUT /api/v1/prediction-models/{id}` - 更新预测模型配置（admin only）
  - [x]8.5 `DELETE /api/v1/prediction-models/{id}` - 删除预测模型（admin only）
  - [x]8.6 `POST /api/v1/prediction-models/{id}/test-connection` - 手动测试连接（admin only）
  - [x]8.7 `GET /api/v1/prediction-models/status` - 获取所有模型运行状态概览（admin + trader 可查看）
  - [x]8.8 在 router.py 中注册新路由

### 前端任务

- [x]Task 9: TypeScript 类型定义 (AC: #1, #2, #3)
  - [x]9.1 新增 `src/types/prediction.ts`
  - [x]9.2 定义 PredictionModel, PredictionModelCreate, PredictionModelUpdate, PredictionModelStatus, ConnectionTestResult, ModelType('wind'|'solar'|'hybrid'), ModelStatus('running'|'error'|'disabled')

- [x] Task 10: API 客户端 (AC: #1, #2, #3)
  - [x]10.1 新增 `src/api/prediction.ts`
  - [x]10.2 实现：getPredictionModels, createPredictionModel, updatePredictionModel, deletePredictionModel, testConnection, getModelStatuses

- [x] Task 11: Composable (AC: #1, #2, #3)
  - [x]11.1 新增 `src/composables/usePredictionModelConfig.ts`
  - [x]11.2 状态管理：models(ref), modelStatuses(ref), isLoading, isTestingConnection
  - [x]11.3 操作：fetchModels, createModel, updateModel, deleteModel, testConnection, fetchStatuses
  - [x]11.4 状态轮询：每30秒自动刷新模型状态（onMounted启动, onUnmounted清理）

- [x] Task 12: 预测模型配置与监控视图 (AC: #1, #2, #3)
  - [x]12.1 新增 `src/views/data/PredictionModelConfigView.vue`
  - [x]12.2 页面布局：
    - 顶部：页面标题 + "新增模型"按钮
    - 状态概览卡片区：运行中/异常/已停用 数量统计（3个 `a-statistic` 卡片）
    - 模型列表表格 `a-table`：模型名称、关联电站、模型类型、API端点（脱敏）、状态（Tag颜色：运行中=green/异常=red/已停用=default）、最后检查时间、操作（编辑/测试连接/启用停用/删除）
    - 新增/编辑模型弹窗 `a-modal`：表单含模型名称、关联电站选择器、模型类型选择、API端点、认证密钥（密码框）、认证方式、调用频率（cron或预设选项）、超时时间
    - 连接测试结果展示：成功显示延迟(ms)绿色Tag，失败显示错误信息红色Alert
  - [x]12.3 在 `data.routes.ts` 中注册路由 `/data/prediction-models`
  - [x]12.4 在 `App.vue` 中添加导航菜单项"预测模型"

### 测试任务

- [x] Task 13: 后端单元测试 (AC: #1, #2, #3, #4)
  - [x]13.1 Schema 层测试（PredictionModelCreate/Read 验证、api_key 脱敏、ConnectionTestResult）
  - [x]13.2 Service 层测试（CRUD 逻辑、test_connection Mock、health_check 状态转换逻辑）
  - [x]13.3 适配器单元测试（GenericPredictionAdapter：Mock httpx 响应、重试逻辑、超时处理、健康检查）
  - [x]13.4 Celery 任务测试（check_prediction_models_health 逻辑、异常告警触发）

- [x] Task 14: 后端集成测试 (AC: #1, #2, #3)
  - [x]14.1 API 端点集成测试（CRUD、测试连接、状态查询、权限 403 校验）
  - [x]14.2 非管理员角色（trader）访问管理端点被拒绝、但可查看状态

- [x] Task 15: 前端测试 (AC: #1, #2, #3)
  - [x]15.1 Composable 测试（usePredictionModelConfig 的 CRUD、状态轮询、连接测试）
  - [x]15.2 视图测试（PredictionModelConfigView 的表格渲染、表单提交、状态卡片、连接测试交互）

## Dev Notes

### 核心设计决策

1. **预测模型为电站级绑定**: 每个预测模型关联特定电站（station_id FK），因为不同电站（风电/光伏）使用不同的预测模型。一个电站可配置多个模型（MVP 仅1个自有模型，架构预留多模型支持）。

2. **适配器模式复用**: 与 Story 2.5 EMS 适配器和 Story 2.6 市场数据适配器架构完全一致：`base.py`（抽象基类）→ `generic.py`（通用实现）→ `__init__.py`（工厂方法）。开发者必须复用此模式，禁止另起炉灶。

3. **健康检查定时任务**: 使用 Celery Beat 每5分钟执行一次健康检查（满足 AC3 "5分钟内发出告警"要求）。状态机：running ↔ error，disabled 需管理员手动切换。

4. **预测数据表设计**: `timeseries.power_predictions` 使用 TimescaleDB hypertable，为 Story 3.2（数据自动拉取）和 Story 3.3（曲线可视化）预埋数据基础。本 Story 仅创建表结构和基础 Repository，不实现数据拉取逻辑。

5. **API Key 加密**: 使用 `cryptography.Fernet`（AES-128-CBC + HMAC-SHA256），与 Story 2.6 市场数据源的加密方案一致。加密密钥通过 `ENCRYPTION_KEY` 环境变量配置。

### 架构约束与模式

**三层架构强制执行**:
- API层（`api/v1/predictions.py`）→ Service层（`services/prediction_service.py`）→ Repository层（`repositories/prediction.py`）
- 禁止跨层调用，业务逻辑全部在 Service 层
- 审计日志统一在 Service 层通过 `audit_service.log()` 记录

**适配器接口规范**:
```python
class BasePredictionAdapter(ABC):
    @abstractmethod
    async def fetch_predictions(self, station_id: str, prediction_date: date) -> list[PredictionRecord]:
        """获取指定电站指定日期的96时段功率预测"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查预测模型API可用性"""
        ...
```

PredictionRecord 数据结构：
```python
@dataclass
class PredictionRecord:
    period: int                    # 1-96
    predicted_power_kw: Decimal    # 预测功率 kW
    confidence_upper_kw: Decimal   # 置信区间上限 kW
    confidence_lower_kw: Decimal   # 置信区间下限 kW
```

**外部API调用规范（与 Story 2.6 一致）**:
- 使用 `httpx.AsyncClient`（版本 0.28.x），不使用 requests
- 超时：由 `prediction_models.timeout_seconds` 配置（默认 30 秒）
- 重试：最多 2 次，指数退避（1s → 2s）
- 每个 health_check 使用 `asyncio.wait_for` 包裹，超时 5 秒

**数据校验规则**:
- period: 范围 1-96（CheckConstraint）
- predicted_power_kw: Decimal(12,2)，≥ 0
- confidence_upper_kw ≥ predicted_power_kw ≥ confidence_lower_kw（CheckConstraint）
- model_type: 枚举 wind/solar/hybrid
- status: 枚举 running/error/disabled

**命名规范（全链路 snake_case）**:
- 表名：`prediction_models`、`power_predictions`
- API 端点：`/api/v1/prediction-models`、`/api/v1/prediction-models/{id}/test-connection`
- Python 文件：`prediction_service.py`、`prediction.py`
- Vue 组件：`PredictionModelConfigView.vue`
- Composable：`usePredictionModelConfig.ts`

### 关键文件路径

**必须新建的文件**:
- `api-server/alembic/versions/011_create_prediction_model_tables.py` - 数据库迁移
- `api-server/app/models/prediction.py` - ORM 模型
- `api-server/app/schemas/prediction.py` - Pydantic Schema
- `api-server/app/repositories/prediction.py` - Repository 层
- `api-server/app/services/prediction_service.py` - Service 层
- `api-server/app/services/prediction_adapters/__init__.py` - 适配器工厂
- `api-server/app/services/prediction_adapters/base.py` - 适配器抽象基类
- `api-server/app/services/prediction_adapters/generic.py` - 通用 API 适配器
- `api-server/app/tasks/prediction_tasks.py` - Celery 定时任务
- `api-server/app/api/v1/predictions.py` - API 路由
- `web-frontend/src/types/prediction.ts` - TypeScript 类型
- `web-frontend/src/api/prediction.ts` - API 客户端
- `web-frontend/src/composables/usePredictionModelConfig.ts` - Composable
- `web-frontend/src/views/data/PredictionModelConfigView.vue` - 管理视图
- 对应测试文件

**必须修改的现有文件**:
- `api-server/app/models/__init__.py` — 注册 PredictionModel, PowerPrediction 模型
- `api-server/app/api/v1/router.py` — 注册 prediction-models 路由
- `api-server/app/tasks/celery_app.py` — 注册 prediction_tasks 模块 + beat schedule（每5分钟健康检查）
- `web-frontend/src/router/modules/data.routes.ts` — 注册预测模型配置路由
- `web-frontend/src/App.vue` — 导航菜单新增"预测模型"入口

### 数据库表设计参考

**prediction_models** (public schema):
```sql
CREATE TABLE public.prediction_models (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    station_id UUID NOT NULL REFERENCES public.power_stations(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(20) NOT NULL DEFAULT 'wind',  -- wind/solar/hybrid
    api_endpoint VARCHAR(500) NOT NULL,
    api_key_encrypted BYTEA,                         -- Fernet AES 加密
    api_auth_type VARCHAR(20) DEFAULT 'api_key',     -- api_key/bearer/none
    call_frequency_cron VARCHAR(50) DEFAULT '0 6,12 * * *',  -- cron 表达式
    timeout_seconds INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'disabled',            -- running/error/disabled
    last_check_at TIMESTAMPTZ,
    last_check_status VARCHAR(20),                    -- success/failed/timeout
    last_check_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_prediction_models_model_type CHECK (model_type IN ('wind', 'solar', 'hybrid')),
    CONSTRAINT ck_prediction_models_status CHECK (status IN ('running', 'error', 'disabled'))
);
CREATE INDEX ix_prediction_models_station_id ON public.prediction_models(station_id);
```

**power_predictions** (timeseries schema, hypertable):
```sql
CREATE TABLE timeseries.power_predictions (
    id UUID DEFAULT gen_random_uuid(),
    prediction_date DATE NOT NULL,                    -- 分区键
    period INTEGER NOT NULL,                          -- 1-96
    station_id UUID NOT NULL REFERENCES public.power_stations(id),
    model_id UUID NOT NULL REFERENCES public.prediction_models(id),
    predicted_power_kw DECIMAL(12,2) NOT NULL,        -- 预测功率 kW
    confidence_upper_kw DECIMAL(12,2) NOT NULL,       -- 置信区间上限
    confidence_lower_kw DECIMAL(12,2) NOT NULL,       -- 置信区间下限
    source VARCHAR(20) DEFAULT 'api',                 -- api/manual
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, prediction_date),
    UNIQUE (station_id, prediction_date, period, model_id),
    CONSTRAINT ck_power_predictions_period CHECK (period >= 1 AND period <= 96),
    CONSTRAINT ck_power_predictions_confidence CHECK (confidence_upper_kw >= predicted_power_kw AND predicted_power_kw >= confidence_lower_kw)
);
-- SELECT create_hypertable('timeseries.power_predictions', 'prediction_date', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
CREATE INDEX ix_power_predictions_station_date ON timeseries.power_predictions(station_id, prediction_date);
```

### 前一故事(2-6)关键经验

1. **Fernet 加密而非 XOR**: API Key 加密必须使用 `cryptography.Fernet`，不使用简化 XOR（Story 2.6 code review 已修复）
2. **httpx.json() 是同步方法**: 测试中 Mock httpx 响应时，`response.json()` 不需要 `await`
3. **Celery Beat 使用 crontab**: 不使用固定间隔秒数，使用 `crontab()` 配置（Story 2.6 code review 修复项 H3）
4. **Redis 注入不可遗漏**: Service 初始化时必须注入 Redis 客户端（Story 2.6 修复项 H1）
5. **asyncio.run() 替代 get_event_loop()**: Celery 任务中使用 `asyncio.run()`（Story 2.6 修复项 H2）
6. **403 权限测试必须覆盖**: 所有 admin-only 端点必须有非管理员访问被拒绝的测试
7. **window.matchMedia mock**: 前端测试需要添加（ant-design-vue 响应式工具需要）
8. **Schema 测试覆盖**: 所有新 Pydantic schema 需要单元测试
9. **操作后自动刷新列表**: 创建/更新/删除后自动重新获取模型列表
10. **错误信息不泄露路径**: 错误消息不包含服务器文件系统路径
11. **models/__init__.py 必须注册**: 新模型必须在 `__init__.py` 中导入

### 技术栈版本

- Python 3.12, FastAPI 0.133.x, SQLAlchemy 2.0.x (async, asyncpg), Pydantic 2.x
- httpx 0.28.x (async HTTP client)
- cryptography (Fernet AES 加密)
- Vue 3.5.x, TypeScript 5.x, Vite 7.x, Pinia 3.0.x, Ant Design Vue 4.2.x
- PostgreSQL 18.x + TimescaleDB 2.23.x
- Celery 5.6.x + Redis 7.x
- Pytest (pytest-asyncio), Vitest 4.0.x

### 与后续 Story 的关系

- **Story 3.2（预测数据自动拉取）**: 将复用本 Story 创建的 `prediction_adapters` 和 `power_predictions` 表，实现 Celery 定时拉取预测数据
- **Story 3.3（预测曲线可视化）**: 将读取 `power_predictions` 表数据，使用 `@ant-design/charts`（G2 v5）渲染96时段功率预测曲线 + 置信区间填充区域
- 本 Story 聚焦于**模型配置管理和健康监控**，不实现数据拉取和可视化

### UX 设计要点

- 模型状态使用 Ant Design Vue `a-tag` 组件：
  - 运行中(running) = `color="green"` + 图标 CheckCircle
  - 异常(error) = `color="red"` + 图标 ExclamationCircle
  - 已停用(disabled) = `color="default"` + 图标 MinusCircle
- 状态概览卡片使用 `a-card` + `a-statistic` 组件，3列布局
- 连接测试结果：成功显示 `a-result status="success"` + 延迟毫秒数，失败显示 `a-result status="error"` + 错误信息
- 模型列表表格列：模型名称、关联电站、类型（Tag）、API端点（截断显示）、状态（Tag）、最后检查、操作
- 新增/编辑表单使用 `a-modal` + `a-form`，认证密钥字段使用 `a-input-password`
- 调用频率提供预设选项（每日2次/每日3次/每6小时）+ 自定义 cron 输入
- 删除操作需 `a-popconfirm` 二次确认

### Project Structure Notes

- 后端新增文件遵循 `api-server/app/{layer}/` 结构
- 预测适配器放在 `app/services/prediction_adapters/` 子目录（与 EMS 适配器、市场数据适配器架构一致）
- 前端新增文件遵循 `web-frontend/src/{category}/` 结构
- 测试文件遵循 `tests/unit/` 和 `tests/integration/` 镜像源代码结构
- 数据库迁移文件编号 011（紧接 010_create_market_data_tables）

### References

- [Source: _bmad-output/planning-artifacts/epics/epic-3-功率预测与数据可视化.md#Story 3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#PowerForecastChart Component]
- [Source: _bmad-output/planning-artifacts/prd/non-functional-requirements.md#NFR17 新模型接入≤1人天]
- [Source: _bmad-output/planning-artifacts/prd/non-functional-requirements.md#NFR2 预测曲线加载<5秒]
- [Source: _bmad-output/implementation-artifacts/2-6-market-data-auto-fetch.md#Dev Notes - 适配器模式、加密方案、经验教训]
- [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Adapter tests: AsyncMock for httpx response.json() returns coroutine; fixed by using MagicMock (httpx .json() is sync)
- Frontend view test: a-card/a-row/a-col stubs with `true` don't render slot content for findAll; fixed by using template stubs `{ template: '<div><slot /></div>' }`

### Completion Notes List

- All 15 tasks implemented and tested
- Backend: 650/650 tests pass (including 18 schema, 20 service, 11 adapter, 4 celery, 15 integration tests for this story)
- Frontend: 378/379 tests pass (13 new tests for this story all pass)
- 1 pre-existing frontend test failure in MarketDataView.test.ts (unrelated to this story)
- Fernet encryption for API keys consistent with Story 2.6 pattern
- Adapter pattern follows base.py → generic.py → __init__.py factory pattern
- Celery Beat health check runs every 5 minutes via crontab
- Code review: 15 fixes applied (5 HIGH, 10 MEDIUM), 5 LOW items deferred by design
- Post-review: 3 test fixes applied (SQL UPDATE mock, composable return type, view mock data)

### Senior Developer Review (AI)

**Reviewer:** hmeng on 2026-03-05
**Outcome:** Changes Requested → Fixes Applied

**Issues Found:** 5 HIGH, 10 MEDIUM, 10 LOW

**Fixes Applied (15 total):**
- H1: SSRF 防护 - `api_endpoint` 增加 URL scheme/hostname 验证，阻止 localhost/169.254.x.x
- H2: API Key 变更审计日志 - `update_model` 中记录 API Key 变更事件
- H3: Celery session 状态损坏 - 使用 `UPDATE` SQL 语句替代 ORM 属性修改 + `expire_on_commit=False`
- H4: 前端 `statusCounts` 改用 `modelStatuses`（全量状态）替代分页 `models`
- H5: 前端表单验证 - 新增/编辑提交前校验必填字段
- M3: 新增 `GET /{model_id}` REST 端点 + `/status` 路由移至路径参数端点之前
- M5: Modal 仅在操作成功后关闭（失败保持打开）
- M6: 筛选变更时重置页码为 1
- M7: 新增 `list_models` 单元测试（修正 19→20 数量不匹配）
- M8: 新增 `asyncio.TimeoutError` 适配器测试
- M10: 集成测试 `test_filter_by_station_id` 验证参数传递
- 新增 3 个 SSRF schema 测试（localhost/metadata/invalid scheme）
- 前端 CRUD 操作改返回 `boolean` 支持 Modal 条件关闭
- 前端 deleteModel/toggleActive 后刷新当前页数据
- Celery 任务移除内联 import，改为顶层导入 `_decrypt_api_key`

**Remaining LOW issues (not fixed):**
- L1: 双重超时冗余 (generic.py)
- L2: 重试循环表达式不够清晰
- L7: 电站列表硬编码限100条
- L8: `api_key_display` 未在 UI 表格显示
- L10: 前端路由仅 admin 但后端 list/status 也允许 trader

**Second Review:** hmeng on 2026-03-05
**Outcome:** Changes Requested → Fixes Applied → Done

**Issues Found:** 3 HIGH, 7 MEDIUM, 3 LOW

**Fixes Applied (10 total):**
- H1: API Key 脱敏改为显示后4位（解密+截取），而非硬编码星号
- H2: SSRF 防护扩展 — 新增 10.0.0.0/8、172.16.0.0/12、192.168.0.0/16 私有网段阻止（使用 ipaddress 模块）
- H3: `get_all_model_statuses` 填充 station_name — 新增 `get_all_active_with_station_name` JOIN power_stations
- M1: 前端 `statusCounts.disabled` 移除 `is_active` 条件判断，直接统计 status='disabled'
- M2: 加密密钥回退时记录 structlog WARNING 日志
- M3: `update_model` 审计日志 `before` 改为记录所有被修改字段的旧值
- M4: `create_model` 连接测试后用 `session.refresh(created)` 替代直接赋值 ORM 属性
- M5: Celery 健康检查改为单次 `asyncio.run` + `asyncio.gather` 批量执行
- M7: `fetch_predictions` 将 httpx.AsyncClient 移至重试循环外，复用 TCP 连接
- 新增 3 个 SSRF 私有网段测试（10.x、172.16.x、192.168.x）

**Remaining LOW issues (not fixed):**
- L1: 双重超时冗余 (generic.py health_check)
- L2: PredictionModelRead.from_model 过度使用 type: ignore
- L3: 前端视图测试覆盖率偏低（仅3个测试）

### Change Log

- 2026-03-05: All tasks (1-15) implemented, tested, and validated
- 2026-03-05: Code review - 15 fixes applied (5 HIGH, 10 MEDIUM), story status → in-progress pending test verification
- 2026-03-05: Post-review test verification - fixed 3 test failures (backend: SQL UPDATE mock assertion; frontend: createModel return boolean, statusCounts mock data). All 650 backend + 378 frontend tests pass. Story status → review
- 2026-03-05: Second code review - 10 fixes applied (3 HIGH, 7 MEDIUM), 3 LOW deferred. All 75 prediction tests pass. Story status → done

### File List

**New Files:**
- `api-server/alembic/versions/011_create_prediction_model_tables.py` - Database migration
- `api-server/app/models/prediction.py` - PredictionModel + PowerPrediction ORM models
- `api-server/app/schemas/prediction.py` - Pydantic schemas (Create/Update/Read/Status/ConnectionTestResult)
- `api-server/app/repositories/prediction.py` - PredictionModelRepository + PowerPredictionRepository
- `api-server/app/services/prediction_service.py` - PredictionService (CRUD, connection test, health check)
- `api-server/app/services/prediction_adapters/base.py` - BasePredictionAdapter ABC
- `api-server/app/services/prediction_adapters/generic.py` - GenericPredictionAdapter (httpx, retry, health check)
- `api-server/app/services/prediction_adapters/__init__.py` - Adapter factory get_adapter()
- `api-server/app/tasks/prediction_tasks.py` - check_prediction_models_health Celery task
- `api-server/app/api/v1/predictions.py` - REST API endpoints (CRUD, test-connection, status)
- `web-frontend/src/types/prediction.ts` - TypeScript types + label/color maps
- `web-frontend/src/api/prediction.ts` - predictionApi client
- `web-frontend/src/composables/usePredictionModelConfig.ts` - Composable with status polling
- `web-frontend/src/views/data/PredictionModelConfigView.vue` - Management view
- `api-server/tests/unit/schemas/test_prediction_schema.py` - 18 schema tests
- `api-server/tests/unit/services/test_prediction_service.py` - 20 service tests
- `api-server/tests/unit/services/test_prediction_adapters.py` - 11 adapter tests
- `api-server/tests/unit/tasks/test_prediction_tasks.py` - 4 celery task tests
- `api-server/tests/integration/api/test_predictions.py` - 15 API integration tests
- `web-frontend/tests/unit/composables/usePredictionModelConfig.test.ts` - 10 composable tests
- `web-frontend/tests/unit/views/data/PredictionModelConfigView.test.ts` - 3 view tests

**Modified Files:**
- `api-server/app/models/__init__.py` - Registered PredictionModel, PowerPrediction
- `api-server/app/api/v1/router.py` - Registered predictions_router
- `api-server/app/tasks/celery_app.py` - Added prediction_tasks module + beat schedule
- `web-frontend/src/router/modules/data.routes.ts` - Added /data/prediction-models route
- `web-frontend/src/App.vue` - Added 预测模型 menu item
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story status
