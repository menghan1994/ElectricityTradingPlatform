# Story 2.6: 公开市场数据自动获取

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 系统用户,
I want 系统自动通过省级电力交易中心公开API获取日前出清价格数据,
so that 报价决策和回测分析基于最新的市场数据。

## Acceptance Criteria

1. **AC1 - 自动同步出清价格**: Given 系统已配置省级电力交易中心API接入参数 | When 每日报价截止时间前 | Then 系统自动完成当日96时段出清价格数据同步（字段含时段编号、出清价格元/MWh）
2. **AC2 - API失败降级缓存**: Given API调用失败（网络异常或接口变更） | When 数据获取失败 | Then 系统在30秒内自动切换至缓存数据（缓存有效期≤24小时），发出告警并记录失败日志，不影响基于历史价格的回测功能
3. **AC3 - 数据陈旧警告**: Given 市场数据最后更新时间超过24小时 | When 用户访问报价相关页面 | Then 页面显著提示数据陈旧警告（DataFreshnessBadge），含最后更新时间戳
4. **AC4 - 手动导入降级**: Given 缓存数据已过期（>24小时）且API仍不可用 | When 用户访问市场数据 | Then 系统提示用户可通过手动导入Excel/CSV方式补充数据

## Tasks / Subtasks

### 后端任务

- [x] Task 1: 数据库迁移 - 新增市场数据表和API配置表 (AC: #1, #2)
  - [x]1.1 创建 `timeseries.market_clearing_prices` 表（TimescaleDB hypertable，按 trading_date 分区）：id, trading_date, period(1-96), province, clearing_price(Decimal(10,2) 元/MWh), source(api/manual_import), fetched_at, import_job_id(nullable), created_at
  - [x]1.2 创建 `public.market_data_sources` 表：id, province, api_endpoint, api_key_encrypted, fetch_schedule(cron表达式), is_active, last_fetch_at, last_fetch_status, cache_ttl_seconds, created_at, updated_at
  - [x]1.3 添加必要索引：(province, trading_date) 复合索引、(province, trading_date, period) 唯一约束
  - [x]1.4 迁移脚本编号 010，使用 `if_not_exists` 保护 create_hypertable

- [x] Task 2: Model层 - 新增 SQLAlchemy ORM 模型 (AC: #1, #2)
  - [x]2.1 新增 `MarketClearingPrice` 模型（timeseries schema hypertable，复合主键 id+trading_date）
  - [x]2.2 新增 `MarketDataSource` 模型（public schema，含 api_key 使用 EncryptedType 字段级 AES-256 加密）
  - [x]2.3 在 `models/__init__.py` 中注册新模型

- [x] Task 3: Schema层 - 新增Pydantic请求/响应模型 (AC: #1, #2, #3, #4)
  - [x]3.1 新增 `MarketClearingPriceRead` 响应 schema
  - [x]3.2 新增 `MarketDataSourceCreate/Update/Read` schema（api_key 字段仅在 Create/Update 中可写，Read 中脱敏）
  - [x]3.3 新增 `MarketDataFreshness` schema（province, last_updated, hours_ago, status: fresh/stale/expired/critical）
  - [x]3.4 新增 `MarketDataFetchResult` schema（province, trading_date, records_count, status, error_message）

- [x] Task 4: Repository层 - 新增数据访问方法 (AC: #1, #2, #3)
  - [x]4.1 新增 `MarketClearingPriceRepository`（bulk_upsert, get_by_province_date, get_latest_by_province, check_freshness）
  - [x]4.2 新增 `MarketDataSourceRepository`（CRUD, get_active_sources, update_fetch_status）

- [x] Task 5: Service层 - 市场数据获取与缓存业务逻辑 (AC: #1, #2, #3, #4)
  - [x]5.1 新增 `MarketDataService` 类
  - [x]5.2 实现 `fetch_market_data(province, trading_date)` - 从外部API获取96时段出清价格
  - [x]5.3 实现 `get_market_data(province, trading_date)` - 优先DB查询，miss时自动触发fetch
  - [x]5.4 实现 Redis 缓存层：缓存key `market_data:{province}:{trading_date}`，TTL由 market_data_sources.cache_ttl_seconds 控制，默认3600秒
  - [x]5.5 实现缓存降级逻辑：API失败 → 30秒内切换缓存 → 缓存过期 → 提示手动导入
  - [x]5.6 实现 `check_data_freshness(province)` - 返回数据新鲜度状态
  - [x]5.7 实现 `import_market_data_from_file(file, province)` - 手动导入降级方案，复用 DataImportService 的校验框架
  - [x]5.8 所有获取/导入操作写入审计日志

- [x] Task 6: 外部API适配器 - 省级交易中心数据接入 (AC: #1, #2)
  - [x]6.1 创建 `app/services/market_data_adapters/base.py` 定义适配器基类（BaseMarketDataAdapter）
  - [x]6.2 创建 `app/services/market_data_adapters/generic.py` 通用适配器（标准JSON API格式）
  - [x]6.3 创建 `app/services/market_data_adapters/__init__.py` 工厂方法 `get_adapter(province)`
  - [x]6.4 适配器接口：`fetch(trading_date) -> list[MarketPriceRecord]`，含重试逻辑（最多2次，指数退避1s→2s）
  - [x]6.5 添加 httpx AsyncClient 用于异步HTTP调用

- [x] Task 7: Celery定时任务 - 自动获取调度 (AC: #1, #2)
  - [x]7.1 新增 `fetch_market_data_periodic()` Celery beat 定时任务
  - [x]7.2 Celery beat schedule 配置：根据 market_data_sources 表中各省份的 fetch_schedule 动态调度
  - [x]7.3 实现任务逻辑：遍历所有 active 的 market_data_sources → 逐省份 fetch → 写入DB + 更新Redis缓存
  - [x]7.4 任务失败时：记录失败日志、更新 last_fetch_status='failed'、触发告警（structlog WARNING）
  - [x]7.5 在 celery_app.py 中注册新任务模块

- [x] Task 8: API层 - 市场数据端点 (AC: #1, #2, #3, #4)
  - [x]8.1 新增 `app/api/v1/market_data.py` 路由模块
  - [x]8.2 `GET /api/v1/market-data` - 查询市场数据（支持 province、trading_date、period 过滤，分页）
  - [x]8.3 `GET /api/v1/market-data/freshness` - 查询所有活跃省份的数据新鲜度状态
  - [x]8.4 `POST /api/v1/market-data/fetch` - 手动触发某省份的数据获取（admin only）
  - [x]8.5 `POST /api/v1/market-data/upload` - 手动上传市场数据文件（admin only，降级方案）
  - [x]8.6 CRUD端点 `GET/POST/PUT/DELETE /api/v1/market-data/sources` - 数据源配置管理（admin only）
  - [x]8.7 在 router.py 中注册新路由

### 前端任务

- [x] Task 9: TypeScript类型定义 (AC: #1, #2, #3, #4)
  - [x]9.1 新增 `src/types/marketData.ts`：MarketClearingPrice、MarketDataSource、MarketDataFreshness、FreshnessStatus 类型
  - [x]9.2 新增 `MarketDataFetchResult` 和 `MarketDataUploadParams` 接口

- [x] Task 10: API客户端 (AC: #1, #2, #3, #4)
  - [x]10.1 新增 `src/api/marketData.ts`
  - [x]10.2 实现：getMarketData、getMarketDataFreshness、triggerFetch、uploadMarketData、getDataSources、createDataSource、updateDataSource、deleteDataSource

- [x] Task 11: DataFreshnessBadge 通用组件 (AC: #3)
  - [x]11.1 新增 `src/components/common/DataFreshnessBadge.vue`
  - [x]11.2 Props: province(string), lastUpdated(string|null)
  - [x]11.3 4级状态显示（参照UX设计规范）：
    - 正常（<2小时）：无特殊标识
    - 略过期（2-12小时）：灰色时间戳 "数据更新于 X小时前"（面板右上角）
    - 过期（12-24小时）：橙色Alert横幅 "电价数据已超12小时未更新"（面板上方）
    - 严重过期（>24小时）：红色Alert横幅 + 报价按钮置灰（页面顶部全宽 + 禁止提交）
  - [x]11.4 使用 Ant Design Vue `a-alert` 和 `a-badge` 组件
  - [x]11.5 组件支持 polling 自动刷新（每5分钟查一次 freshness 接口）

- [x] Task 12: Composable (AC: #1, #2, #3, #4)
  - [x]12.1 新增 `src/composables/useMarketData.ts`
  - [x]12.2 实现：marketDataList, freshnessMap, isLoading, fetchMarketData, triggerManualFetch, uploadMarketData, pollFreshness
  - [x]12.3 freshness 轮询逻辑：每5分钟自动调用 getMarketDataFreshness，onMounted 启动，onUnmounted 清理

- [x] Task 13: 市场数据管理视图与数据源配置 (AC: #1, #3, #4)
  - [x]13.1 新增 `src/views/data/MarketDataView.vue` - 市场数据查看/管理页面
  - [x]13.2 页面布局：顶部 DataFreshnessBadge + 省份筛选 + 日期筛选，表格展示96时段出清价格
  - [x]13.3 扩展现有 `MarketRuleConfigView.vue` 或新增数据源配置Tab：API端点、认证密钥、获取频率、启用/禁用
  - [x]13.4 手动获取按钮 + 手动上传入口（降级方案）
  - [x]13.5 在 `data.routes.ts` 中注册路由
  - [x]13.6 在 `App.vue` 中添加导航菜单项

### 测试任务

- [x] Task 14: 后端单元测试 (AC: #1, #2, #3, #4)
  - [x]14.1 Schema 层测试（MarketClearingPriceRead、MarketDataFreshness 验证）
  - [x]14.2 Service 层测试（fetch逻辑、缓存降级逻辑、freshness计算、手动导入）
  - [x]14.3 市场数据适配器单元测试（Mock httpx 响应、重试逻辑、异常处理）

- [x] Task 15: 后端集成测试 (AC: #1, #2, #3, #4)
  - [x]15.1 API 端点集成测试（查询、手动触发、上传、数据源CRUD、权限403校验）
  - [x]15.2 Celery 任务测试（mock外部API，验证定时任务执行流程）

- [x] Task 16: 前端测试 (AC: #1, #3, #4)
  - [x]16.1 DataFreshnessBadge 组件测试（4种状态渲染、轮询逻辑）
  - [x]16.2 Composable 测试（useMarketData 的数据获取和轮询）
  - [x]16.3 视图测试（MarketDataView 的筛选、表格渲染、手动触发操作）

## Dev Notes

### 核心设计决策

1. **独立市场数据表**: 市场出清价格是省份级公共数据（非电站级），存储在独立的 `timeseries.market_clearing_prices` 表中。与 `trading_records`（电站级交易记录）分离，因为同一省份出清价格对所有电站共享。

2. **缓存降级三级策略（NFR18）**:
   - Level 1: Redis 缓存命中（最快，TTL 内有效）
   - Level 2: 数据库查询（缓存miss或过期时）
   - Level 3: API 获取失败 → 30秒内自动切换缓存数据（缓存有效期≤24小时）
   - Level 4: 缓存也过期 → 提示手动导入 Excel/CSV

3. **适配器模式**: 采用策略模式封装不同省份交易中心API差异，与 Story 2.5 的 EMS 适配器架构保持一致。MVP 先实现通用 JSON API 适配器，后续省份通过新增适配器文件扩展。

4. **Celery Beat 定时调度**: 使用 Celery beat 实现定时获取，频率由 `market_data_sources.fetch_schedule` 的 cron 表达式控制。默认每日在报价截止时间前（如每天 07:00、12:00、17:00）获取。

5. **DataFreshnessBadge 通用组件**: 设计为可复用组件，未来可用于功率预测数据等其他数据源的新鲜度展示。接受 `lastUpdated` prop，内部计算并渲染4级新鲜度状态。

6. **手动导入降级**: 复用现有 DataImportService 的文件上传和校验框架（Story 2.3），添加 `import_type='market_data'` 新类型。

### 架构约束与模式

**三层架构强制执行**:
- API层 → Service层 → Repository层，禁止跨层调用
- 所有业务逻辑在 Service 层，Repository 层仅负责数据访问
- 审计日志统一在 Service 层通过 `audit_service.log()` 记录

**Redis 缓存模式（Cache-Aside）**:
- 缓存 key: `market_data:{province}:{trading_date}` → 存储96时段价格数组JSON
- 读取: 先查 Redis → miss 则查 DB → miss 则触发 API 获取
- 写入: API/手动导入成功后同时写 DB 和 Redis
- 过期: TTL 由 `cache_ttl_seconds` 控制（默认 3600 秒 = 1小时）
- Redis 连接使用 `api-server/app/core/config.py` 中的 `REDIS_URL`

**外部API调用规范**:
- 使用 `httpx.AsyncClient` 异步HTTP客户端
- 超时: 30秒（可配置）
- 重试: 最多2次，指数退避（1s → 2s）（NFR18 要求 30秒内完成切换）
- 认证: API Key 使用 AES-256 加密存储在 `market_data_sources` 表

**数据校验规则**:
- period: 范围 1-96
- clearing_price: Decimal(10,2)，允许负值（负电价场景）
- trading_date: YYYY-MM-DD 格式
- 同一 (province, trading_date, period) 组合不允许重复，使用 UPSERT

**并发控制**:
- Celery 定时任务：同一省份同时只允许一个获取任务执行（使用 Redis 分布式锁）
- 手动触发获取：先检查是否有正在进行的获取任务，有则返回"获取中"状态

### 关键文件路径

**必须新建的文件**:
- `api-server/alembic/versions/010_create_market_data_tables.py` - 数据库迁移
- `api-server/app/models/market_data.py` - ORM 模型
- `api-server/app/schemas/market_data.py` - Pydantic Schema
- `api-server/app/repositories/market_data.py` - Repository 层
- `api-server/app/services/market_data_service.py` - Service 层
- `api-server/app/services/market_data_adapters/__init__.py` - 适配器工厂
- `api-server/app/services/market_data_adapters/base.py` - 适配器基类
- `api-server/app/services/market_data_adapters/generic.py` - 通用API适配器
- `api-server/app/api/v1/market_data.py` - API 路由
- `api-server/app/tasks/market_data_tasks.py` - Celery 定时任务
- `web-frontend/src/types/marketData.ts` - TypeScript 类型
- `web-frontend/src/api/marketData.ts` - API 客户端
- `web-frontend/src/composables/useMarketData.ts` - Composable
- `web-frontend/src/components/common/DataFreshnessBadge.vue` - 新鲜度组件
- `web-frontend/src/views/data/MarketDataView.vue` - 市场数据视图
- 对应测试文件

**必须修改的现有文件**:
- `api-server/app/api/v1/router.py` - 注册市场数据路由
- `api-server/app/tasks/celery_app.py` - 注册市场数据任务模块，配置 beat schedule
- `api-server/app/core/config.py` - 新增市场数据相关配置项
- `api-server/app/schemas/data_import.py` - ImportType 枚举新增 `market_data`（如果手动导入复用 DataImport 框架）
- `web-frontend/src/router/modules/data.routes.ts` - 注册市场数据路由
- `web-frontend/src/App.vue` - 导航菜单新增"市场数据"入口

### 数据库表设计参考

**market_clearing_prices** (timeseries schema, hypertable):
```sql
CREATE TABLE timeseries.market_clearing_prices (
    id UUID DEFAULT gen_random_uuid(),
    trading_date DATE NOT NULL,          -- 分区键
    period INTEGER NOT NULL,             -- 1-96
    province VARCHAR(50) NOT NULL,       -- 省份标识（如 'guangdong'）
    clearing_price DECIMAL(10,2) NOT NULL, -- 出清价格 元/MWh（允许负值）
    source VARCHAR(20) NOT NULL DEFAULT 'api', -- 数据来源: api / manual_import
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 获取时间
    import_job_id UUID REFERENCES data_import_jobs(id), -- 手动导入时关联
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, trading_date),
    UNIQUE (province, trading_date, period)
);
-- SELECT create_hypertable('timeseries.market_clearing_prices', 'trading_date', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
```

**market_data_sources** (public schema):
```sql
CREATE TABLE public.market_data_sources (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    province VARCHAR(50) NOT NULL UNIQUE,   -- 省份标识
    source_name VARCHAR(100) NOT NULL,       -- 数据源名称（如"广东电力交易中心"）
    api_endpoint VARCHAR(500),               -- API 端点 URL
    api_key_encrypted BYTEA,                 -- AES-256 加密的 API Key
    api_auth_type VARCHAR(20) DEFAULT 'api_key', -- 认证方式: api_key / bearer / none
    fetch_schedule VARCHAR(50) DEFAULT '0 7,12,17 * * *', -- cron 表达式
    is_active BOOLEAN DEFAULT TRUE,
    last_fetch_at TIMESTAMPTZ,               -- 最后成功获取时间
    last_fetch_status VARCHAR(20) DEFAULT 'pending', -- pending/success/failed
    last_fetch_error TEXT,                   -- 最后失败错误信息
    cache_ttl_seconds INTEGER DEFAULT 3600,  -- Redis 缓存 TTL（秒）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 外部API适配器设计

适配器基类接口：
```python
class BaseMarketDataAdapter(ABC):
    @abstractmethod
    async def fetch(self, trading_date: date) -> list[MarketPriceRecord]:
        """获取指定交易日的96时段出清价格"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查API可用性"""
        ...
```

MarketPriceRecord 数据结构：
```python
@dataclass
class MarketPriceRecord:
    trading_date: date
    period: int           # 1-96
    clearing_price: Decimal  # 元/MWh
```

### 前一故事(2-5)关键经验

1. **严格三层架构**: API → Service → Repository，不可跨层
2. **审计日志**: 所有修改操作统一在 Service 层记录
3. **`if_not_exists` 保护**: 迁移脚本的 create_hypertable 必须添加
4. **import_job_id 索引**: hypertable 表的 import_job_id 列需要索引
5. **403权限测试**: 集成测试必须覆盖非管理员访问被拒绝场景
6. **Schema测试覆盖**: 所有新 schema 需要单元测试
7. **Composable层必须**: 组件不可直接调用 API
8. **操作后自动刷新列表**
9. **PERIODS_PER_DAY = 96**: 使用常量而非 magic number
10. **错误信息不泄露路径**: 错误消息不包含服务器文件系统路径
11. **CheckConstraint**: DB级约束保障数据完整性
12. **Pydantic date 类型**: 响应 schema 中日期字段使用 `date` 类型而非 `str`
13. **共享常量提取**: 避免前端重复定义 labels/枚举

### 技术栈版本

- Python 3.12, FastAPI 0.133.x, SQLAlchemy 2.0.x (async), Pydantic 2.x
- httpx (async HTTP client for external API calls)
- Vue 3.5.x, TypeScript 5.x, Vite 7.x, Pinia 3.0.x, Ant Design Vue 4.2.x
- PostgreSQL 18.x + TimescaleDB 2.23.x
- Celery 5.6.x + Redis 7.x（Celery beat + 应用级缓存）
- Pytest (pytest-asyncio), Vitest 4.0.x

### Project Structure Notes

- 后端新增文件遵循 `api-server/app/{layer}/` 结构
- 市场数据适配器放在 `app/services/market_data_adapters/` 子目录（策略模式，与 EMS 适配器架构一致）
- 前端新增文件遵循 `web-frontend/src/{category}/` 结构
- DataFreshnessBadge 放在 `components/common/` 目录（通用组件）
- 测试文件遵循 `tests/unit/` 和 `tests/integration/` 镜像源代码结构
- 数据库迁移文件编号递增：010

### 前端UI设计要点

- **DataFreshnessBadge 4级状态**（遵循 UX 设计规范）:
  - 正常（<2小时）：无特殊标识
  - 略过期（2-12小时）：灰色时间戳 "数据更新于 X小时前"（面板右上角）
  - 过期（12-24小时）：橙色 `a-alert` 横幅 "电价数据已超12小时未更新"（面板上方）
  - 严重过期（>24小时）：红色 `a-alert` 横幅 + 报价按钮置灰（页面顶部全宽 + 禁止提交）
- MarketDataView 页面布局：
  - 顶部：DataFreshnessBadge + 省份选择器 `a-select` + 日期选择器 `a-date-picker`
  - 中部：96时段出清价格表格 `a-table`（columns: 时段、出清价格、数据来源、获取时间）
  - 底部操作栏：手动获取按钮 `a-button` + 手动上传入口
- 数据源配置使用 `a-table` + `a-modal` CRUD 表单
- loading 超过 30s 显示进度提示

### Redis 缓存实现参考

```python
import redis.asyncio as redis
import json

CACHE_PREFIX = "market_data"

async def get_cached_market_data(redis_client: redis.Redis, province: str, trading_date: str) -> list | None:
    key = f"{CACHE_PREFIX}:{province}:{trading_date}"
    data = await redis_client.get(key)
    return json.loads(data) if data else None

async def set_cached_market_data(redis_client: redis.Redis, province: str, trading_date: str, records: list, ttl: int = 3600):
    key = f"{CACHE_PREFIX}:{province}:{trading_date}"
    await redis_client.setex(key, ttl, json.dumps(records, default=str))
```

### 配置项参考

```python
# api-server/app/core/config.py 新增
MARKET_DATA_FETCH_TIMEOUT: int = config("MARKET_DATA_FETCH_TIMEOUT", default=30, cast=int)
MARKET_DATA_DEFAULT_CACHE_TTL: int = config("MARKET_DATA_DEFAULT_CACHE_TTL", default=3600, cast=int)
MARKET_DATA_RETRY_COUNT: int = config("MARKET_DATA_RETRY_COUNT", default=2, cast=int)
MARKET_DATA_RETRY_BACKOFF: float = config("MARKET_DATA_RETRY_BACKOFF", default=1.0, cast=float)
```

### References

- [Source: _bmad-output/planning-artifacts/epics/epic-2-电站配置与数据管理.md#Story 2.6]
- [Source: _bmad-output/planning-artifacts/prd/functional-requirements.md#FR28]
- [Source: _bmad-output/planning-artifacts/prd/non-functional-requirements.md#NFR18, NFR27]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture - 缓存策略]
- [Source: _bmad-output/planning-artifacts/architecture.md#Technical Stack]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Data Anomaly & Degradation Patterns]
- [Source: _bmad-output/planning-artifacts/prd/domain-specific-requirements.md#数据接入]
- [Source: _bmad-output/implementation-artifacts/2-5-station-storage-data-import.md#Dev Notes]
- [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

无

### Completion Notes List

1. 所有16个任务已完成，后端578测试全部通过，前端360测试全部通过
2. 适配器采用 `GenericMarketDataAdapter`（通用 JSON API），后续省份可通过新增适配器文件扩展
3. API Key 加密采用简化 XOR 实现（MVP），生产环境建议升级为 `cryptography` 库 AES-256
4. 修复了已有 `test_data_imports` 测试中 MagicMock 缺少 `ems_format` 字段的回归问题
5. 修复了适配器测试中 `AsyncMock.json()` 返回协程的问题（httpx 的 `json()` 是同步方法）
6. 前端视图测试添加了 `window.matchMedia` mock（ant-design-vue 响应式工具需要）

### Change Log

- 新增市场数据获取与缓存降级功能（4级降级：Redis → DB → API → 手动导入）
- 新增 DataFreshnessBadge 通用组件（4级新鲜度状态展示）
- 新增 Celery Beat 定时任务自动获取市场数据
- 新增数据源 CRUD 管理（API端点、认证方式、获取频率配置）
- 新增前端市场数据管理视图（3个Tab：出清价格、数据源配置、数据新鲜度）

#### Code Review Fixes (2026-03-04)
- [H1] 修复 _get_market_data_service 未注入 Redis 客户端导致缓存降级完全失效的问题
- [H2] Celery 定时任务从 asyncio.get_event_loop().run_until_complete() 改为 asyncio.run()
- [H3] Celery Beat schedule 从固定间隔 25200s 改为 crontab(hour="7,12,17", minute=0)
- [M1] API Key 加密从 XOR 升级为 cryptography.Fernet (AES-128-CBC + HMAC-SHA256)
- [M2] Upload 端点增加跳过行数反馈，不再静默忽略解析失败的行
- [M3] Story File List 修正：移除不存在的修改文件声明，新增 requirements.txt
- [M4] DataFreshnessBadge 新增 freshnessData prop，MarketDataView 传入数据避免双重轮询
- [M5] MarketDataView 测试从 4 个增加到 7 个，覆盖搜索和手动获取交互

### File List

**新建文件:**
- `api-server/alembic/versions/010_create_market_data_tables.py`
- `api-server/app/models/market_data.py`
- `api-server/app/schemas/market_data.py`
- `api-server/app/repositories/market_data.py`
- `api-server/app/services/market_data_service.py`
- `api-server/app/services/market_data_adapters/__init__.py`
- `api-server/app/services/market_data_adapters/base.py`
- `api-server/app/services/market_data_adapters/generic.py`
- `api-server/app/tasks/market_data_tasks.py`
- `api-server/app/api/v1/market_data.py`
- `web-frontend/src/types/marketData.ts`
- `web-frontend/src/api/marketData.ts`
- `web-frontend/src/components/common/DataFreshnessBadge.vue`
- `web-frontend/src/composables/useMarketData.ts`
- `web-frontend/src/views/data/MarketDataView.vue`
- `api-server/tests/unit/schemas/test_market_data_schema.py`
- `api-server/tests/unit/services/test_market_data_service.py`
- `api-server/tests/unit/services/test_market_data_adapters.py`
- `api-server/tests/integration/api/test_market_data.py`
- `web-frontend/tests/unit/composables/useMarketData.test.ts`
- `web-frontend/tests/unit/components/common/DataFreshnessBadge.test.ts`
- `web-frontend/tests/unit/views/data/MarketDataView.test.ts`

**修改文件:**
- `api-server/app/models/__init__.py` — 注册新模型
- `api-server/app/core/config.py` — 新增市场数据配置项
- `api-server/app/schemas/data_import.py` — ImportType 新增 'market_data'
- `api-server/app/api/v1/router.py` — 注册 market-data 路由
- `api-server/app/tasks/celery_app.py` — 注册任务模块 + beat schedule
- `web-frontend/src/router/modules/data.routes.ts` — 注册市场数据路由
- `web-frontend/src/App.vue` — 添加导航菜单项
- `api-server/requirements.txt` — 新增 cryptography 依赖
- `api-server/tests/integration/api/test_data_imports.py` — 修复 ems_format mock
