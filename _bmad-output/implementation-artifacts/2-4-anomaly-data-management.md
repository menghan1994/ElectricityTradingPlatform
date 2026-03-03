# Story 2.4: 异常数据管理与修正

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 系统管理员（老周）,
I want 按异常类型和导入批次筛选查看异常数据，并进行修正操作,
So that 我能快速处理数据质量问题，确保系统数据准确可用。

## Acceptance Criteria

1. **Given** 存在已标记异常的导入数据 **When** 管理员按异常类型（缺失/格式错误/超范围/重复）筛选 **Then** 异常数据列表按类型分组展示

2. **Given** 管理员查看异常数据列表 **When** 管理员按导入批次筛选 **Then** 仅显示该批次的异常数据

3. **Given** 管理员选中一条异常数据 **When** 管理员编辑修正该条数据并保存 **Then** 数据更新成功，异常标记移除，修正操作记录写入审计日志

4. **Given** 管理员选中多条异常数据 **When** 管理员执行"批量删除"操作 **Then** 选中数据被删除，操作记录写入审计日志

5. **Given** 管理员判断某条异常数据为正常情况（如节假日停市） **When** 管理员标记"已确认正常" **Then** 异常标记移除，数据保留，操作记录写入审计日志

## Tasks / Subtasks

- [ ] Task 1: Schema 层 — 异常管理请求/响应定义 (AC: #1, #2, #3, #4, #5)
  - [ ] 1.1 在 `app/schemas/data_import.py` 新增 `AnomalyCorrectRequest` schema：corrected_value (str, 修正后的值)
  - [ ] 1.2 新增 `AnomalyBulkActionRequest` schema：anomaly_ids (list[UUID])，action (Literal["delete", "confirm_normal"])
  - [ ] 1.3 新增 `AnomalyBulkActionResponse` schema：affected_count (int)，action (str)
  - [ ] 1.4 新增 `AnomalyDetailRead` schema：扩展 ImportAnomalyRead，关联 import_job 的 original_file_name 和 station_id 信息
  - [ ] 1.5 新增 `AnomalyFilterParams` schema 或直接在端点用 Query 参数：anomaly_type (可选)、status (可选，默认 pending)、import_job_id (可选)

- [ ] Task 2: Repository 层 — 异常数据访问扩展 (AC: #1, #2, #3, #4, #5)
  - [ ] 2.1 在 `ImportAnomalyRepository` 新增 `get_by_id(anomaly_id)` → 单条异常记录（若未继承自 BaseRepository）
  - [ ] 2.2 新增 `list_all_anomalies(page, page_size, anomaly_type_filter, status_filter, import_job_id_filter)` → 跨批次分页查询，支持三重筛选
  - [ ] 2.3 新增 `update_status(anomaly_id, new_status)` → 更新单条异常状态
  - [ ] 2.4 新增 `bulk_update_status(anomaly_ids, new_status)` → 批量更新状态，返回 affected 行数
  - [ ] 2.5 新增 `update_anomaly_value(anomaly_id, corrected_value, new_status)` → 修正数据时同时更新 raw_value 和 status
  - [ ] 2.6 新增 `get_summary_all(import_job_id_filter, status_filter)` → 全局异常分类统计（可选按 job 或状态筛选）

- [ ] Task 3: Service 层 — 异常管理业务逻辑 (AC: #3, #4, #5)
  - [ ] 3.1 在 `DataImportService` 新增 `get_anomaly(anomaly_id)` — 获取单条异常详情
  - [ ] 3.2 新增 `correct_anomaly(anomaly_id, corrected_value, current_user, client_ip)`:
    - 校验异常存在且状态为 pending
    - 对 corrected_value 执行与导入时相同的数据校验（日期格式/时段范围/价格格式）
    - 若校验通过：将修正值写入 `timeseries.trading_records`（INSERT 或 UPDATE）
    - 更新异常状态为 corrected
    - 审计日志记录（修正前值、修正后值、操作人、时间）
  - [ ] 3.3 新增 `confirm_anomaly_normal(anomaly_id, current_user, client_ip)`:
    - 校验异常存在且状态为 pending
    - 更新状态为 confirmed_normal
    - 审计日志记录
  - [ ] 3.4 新增 `bulk_delete_anomalies(anomaly_ids, current_user, client_ip)`:
    - 校验所有 anomaly_ids 存在且状态为 pending
    - 批量更新状态为 deleted
    - 对 duplicate 类型异常：删除对应 trading_records 中的记录（如有）
    - 审计日志记录（含总数）
  - [ ] 3.5 新增 `bulk_confirm_normal(anomaly_ids, current_user, client_ip)`:
    - 校验所有 anomaly_ids 存在且状态为 pending
    - 批量更新状态为 confirmed_normal
    - 审计日志记录（含总数）
  - [ ] 3.6 新增 `list_anomalies_global(page, page_size, anomaly_type, status, import_job_id)`:
    - 全局异常列表查询（跨导入批次）
    - 调用 repository 层 list_all_anomalies
  - [ ] 3.7 在 `correct_anomaly` 中实现修正值写入 trading_records 的逻辑：
    - 解析 corrected_value（根据 field_name 判断修正哪个字段）
    - 若 anomaly_type 为 missing/format_error/out_of_range：尝试 INSERT 或 UPDATE trading_records
    - 若 anomaly_type 为 duplicate：不写入 trading_records（重复记录修正仅更新标记）
    - 更新 DataImportJob 的 success_records/failed_records 计数

- [ ] Task 4: API 端点 — 异常管理接口 (AC: #1, #2, #3, #4, #5)
  - [ ] 4.1 新建 `app/api/v1/anomalies.py`（独立路由模块，不塞入 data_imports.py）：
    - `GET /api/v1/anomalies` — 全局异常列表（跨导入批次），query params: page, page_size, anomaly_type, status, import_job_id，admin-only
    - `GET /api/v1/anomalies/{anomaly_id}` — 单条异常详情，admin-only
    - `PATCH /api/v1/anomalies/{anomaly_id}/correct` — 修正异常数据，body: AnomalyCorrectRequest，admin-only
    - `PATCH /api/v1/anomalies/{anomaly_id}/confirm-normal` — 标记为已确认正常，admin-only
    - `POST /api/v1/anomalies/bulk-action` — 批量操作（删除/确认正常），body: AnomalyBulkActionRequest，admin-only
  - [ ] 4.2 更新 `app/api/v1/router.py`：注册 anomalies 路由前缀 `/anomalies`
  - [ ] 4.3 保留 `GET /api/v1/data-imports/{job_id}/anomalies` 端点不变（按批次查看，Story 2.3 已实现）

- [ ] Task 5: 前端 — TypeScript 类型与 API 封装 (AC: #1-#5)
  - [ ] 5.1 在 `src/types/dataImport.ts` 新增类型：
    - `AnomalyCorrectRequest = { corrected_value: string }`
    - `AnomalyBulkActionRequest = { anomaly_ids: string[], action: 'delete' | 'confirm_normal' }`
    - `AnomalyBulkActionResponse = { affected_count: number, action: string }`
  - [ ] 5.2 新建 `src/api/anomaly.ts`（独立 API 文件）：
    - `listAnomalies(params: { page?, page_size?, anomaly_type?, status?, import_job_id? })` — GET
    - `getAnomaly(anomalyId: string)` — GET
    - `correctAnomaly(anomalyId: string, data: AnomalyCorrectRequest)` — PATCH
    - `confirmAnomalyNormal(anomalyId: string)` — PATCH
    - `bulkAction(data: AnomalyBulkActionRequest)` — POST

- [ ] Task 6: 前端 — Composable 与组件 (AC: #1-#5)
  - [ ] 6.1 新建 `src/composables/useAnomalyManagement.ts`：
    - `anomalies` ref + `total` ref + `isLoading` ref
    - `selectedIds` ref (Set<string>) — 批量选择管理
    - `loadAnomalies(filters)` — 加载异常列表
    - `correctAnomaly(anomalyId, correctedValue)` — 修正单条
    - `confirmNormal(anomalyId)` — 确认单条正常
    - `bulkDelete()` — 批量删除选中项
    - `bulkConfirmNormal()` — 批量确认正常
    - 操作成功后自动刷新列表
  - [ ] 6.2 新建 `src/views/data/AnomalyManagementView.vue`：异常数据管理主页面
    - 顶部筛选区：导入批次选择器 + 异常类型选择器 + 状态选择器 + 查询按钮
    - 异常统计卡片：按类型显示 pending 状态数量
    - 异常数据表格：`a-table` 支持 rowSelection 多选，列：行号、异常类型（Tag 标签）、字段名、原始值、描述、状态、操作
    - 批量操作工具栏：选中 N 项后显示"批量删除"和"批量确认正常"按钮
    - 操作列：每行有"修正"（弹出 Modal）、"确认正常"、"删除"按钮（仅 pending 状态显示）
  - [ ] 6.3 新建 `src/components/data/AnomalyCorrectModal.vue`：修正弹窗组件
    - 显示异常详情（行号、字段、原始值、异常类型、描述）
    - 输入框输入修正值
    - 修正值前端基础校验（非空）
    - 确认/取消按钮
  - [ ] 6.4 新建 `src/components/data/AnomalyFilterBar.vue`：筛选栏组件
    - 导入批次下拉：调用 listImportJobs 获取批次列表
    - 异常类型下拉：缺失/格式错误/超范围/重复
    - 状态下拉：待处理/已确认正常/已修正/已删除（默认选中"待处理"）
    - 查询/重置按钮

- [ ] Task 7: 前端 — 路由与导航 (AC: #1)
  - [ ] 7.1 更新 `src/router/modules/data.routes.ts`：新增异常管理路由 `/data/anomalies`，权限 `meta: { roles: ['admin'] }`
  - [ ] 7.2 更新 `src/App.vue`：侧边栏"数据管理"菜单分组下新增"异常数据"菜单项（仅 admin 可见），位于"数据导入"下方
  - [ ] 7.3 在 `ImportResultSummary.vue` 中为异常汇总行添加"查看详情"链接，跳转至异常管理页并预设 import_job_id 筛选

- [ ] Task 8: 后端测试 (AC: #1-#5)
  - [ ] 8.1 `tests/unit/schemas/test_anomaly_schema.py`：新增 schema 校验测试
    - AnomalyCorrectRequest：corrected_value 非空校验
    - AnomalyBulkActionRequest：anomaly_ids 非空列表校验、action 有效值校验
  - [ ] 8.2 `tests/unit/services/test_anomaly_management_service.py`：Service 层测试
    - correct_anomaly：成功修正 + 审计日志
    - correct_anomaly：异常不存在返回 ANOMALY_NOT_FOUND
    - correct_anomaly：非 pending 状态不可修正
    - correct_anomaly：修正值校验失败返回错误
    - confirm_anomaly_normal：成功确认 + 审计日志
    - confirm_anomaly_normal：非 pending 状态不可确认
    - bulk_delete_anomalies：成功批量删除 + 审计日志
    - bulk_delete_anomalies：包含非 pending 状态的 ID 返回错误
    - bulk_confirm_normal：成功批量确认 + 审计日志
    - list_anomalies_global：三重筛选正确传递
  - [ ] 8.3 `tests/integration/api/test_anomalies.py`：API 集成测试
    - GET /anomalies 返回分页列表
    - GET /anomalies?anomaly_type=missing 按类型筛选
    - GET /anomalies?import_job_id=xxx 按批次筛选
    - GET /anomalies?status=pending 按状态筛选
    - PATCH /anomalies/{id}/correct 成功修正返回 200
    - PATCH /anomalies/{id}/confirm-normal 成功确认返回 200
    - POST /anomalies/bulk-action delete 成功返回 affected_count
    - POST /anomalies/bulk-action confirm_normal 成功返回 affected_count
    - 非 admin 访问返回 403（4 个端点各一个）

- [ ] Task 9: 前端测试 (AC: #1-#5)
  - [ ] 9.1 `tests/unit/composables/useAnomalyManagement.test.ts`：composable 测试
    - loadAnomalies：调用 API 并更新状态
    - correctAnomaly：调用 API + 刷新列表
    - confirmNormal：调用 API + 刷新列表
    - bulkDelete：调用 API + 清空选中 + 刷新列表
    - bulkConfirmNormal：调用 API + 清空选中 + 刷新列表
  - [ ] 9.2 `tests/unit/components/data/AnomalyCorrectModal.test.ts`：修正弹窗测试
    - 渲染异常详情信息
    - 输入修正值后点击确认触发事件
    - 空值校验阻止提交
  - [ ] 9.3 `tests/unit/views/data/AnomalyManagementView.test.ts`：页面测试
    - 渲染筛选区 + 表格 + 批量操作栏
    - 筛选条件变更触发列表刷新
    - 勾选行后显示批量操作按钮
    - 非 admin 不可访问

## Dev Notes

### 核心设计决策

**本 Story 是 Epic 2 第四个故事**，直接构建在 Story 2.3（历史数据导入）之上。Story 2.3 已创建 `import_anomalies` 表和基础读取功能，本 Story 扩展为完整的异常管理 CRUD。

**关键设计原则：**

1. **独立 API 路由模块**：异常管理端点从 `data_imports.py` 中独立为 `anomalies.py`（`/api/v1/anomalies`），因为异常管理是跨批次的全局操作，不应嵌套在 `/data-imports/{job_id}/` 下
2. **软删除模式**：删除操作更新 `status = 'deleted'`，不物理删除记录，保留审计可追溯性
3. **状态机约束**：仅 `pending` 状态的异常可被操作（修正/确认正常/删除），已处理的异常不可再次修改
4. **修正值校验**：修正数据时执行与导入时相同的校验规则（日期格式、时段范围 1-96、价格格式），不接受仍然不合法的修正值
5. **修正联动 trading_records**：修正操作不仅更新异常状态，还需将修正值写入 `timeseries.trading_records` 表（除 duplicate 类型外）
6. **批量操作**：支持多选后批量删除和批量确认正常，提升处理效率（如节假日停市通常是批量操作场景）
7. **审计全覆盖**：所有修改操作（修正、确认正常、批量删除、批量确认）均记录审计日志

### 已有基础设施（Story 2.3 已实现，直接复用）

**数据模型 — `import_anomalies` 表（public schema）：**

```sql
CREATE TABLE import_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_job_id UUID NOT NULL REFERENCES data_import_jobs(id),
    row_number INTEGER NOT NULL,
    anomaly_type VARCHAR(20) NOT NULL,  -- 'missing'|'format_error'|'out_of_range'|'duplicate'
    field_name VARCHAR(50) NOT NULL,
    raw_value TEXT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending'|'confirmed_normal'|'corrected'|'deleted'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 索引: ix_import_anomalies_job_id, ix_import_anomalies_type
```

**已有后端代码：**
- `app/models/data_import.py` — `ImportAnomaly` SQLAlchemy 模型，状态字段已支持全生命周期
- `app/schemas/data_import.py` — `ImportAnomalyRead`、`AnomalyType`、`AnomalyStatus`、`ImportAnomalySummary`、`ImportAnomalyListResponse`
- `app/repositories/data_import.py` — `ImportAnomalyRepository`：`bulk_create()`、`list_by_job()`、`get_summary_by_job()`
- `app/services/data_import_service.py` — `get_anomalies()` 按 job 查询异常列表
- `app/api/v1/data_imports.py` — `GET /data-imports/{job_id}/anomalies` 按批次查看

**已有前端代码：**
- `src/types/dataImport.ts` — `ImportAnomaly`、`AnomalyType`、`AnomalyStatus`、`AnomalySummary` 接口
- `src/api/dataImport.ts` — `getImportAnomalies(jobId, params)` 查询方法
- `src/components/data/ImportResultSummary.vue` — 异常汇总表格（anomaly_type + count）

**无需新建 Alembic 迁移**：import_anomalies 表结构已完整，status 字段已支持 pending/confirmed_normal/corrected/deleted。

### 状态机设计

**异常状态转换规则（强制）：**

```
pending → confirmed_normal  (管理员确认为正常)
pending → corrected         (管理员修正数据)
pending → deleted           (管理员删除数据)

confirmed_normal → (不可变更)
corrected → (不可变更)
deleted → (不可变更)
```

已处理的异常（非 pending 状态）禁止再次修改。前后端均需校验。

### 修正数据写入 trading_records 逻辑

修正操作根据 anomaly_type 决定写入行为：

| anomaly_type | 修正行为 | trading_records 操作 |
|-------------|---------|---------------------|
| `format_error` | 管理员输入正确格式的值 | 解析修正值 → INSERT trading_records（同一 station_id + trading_date + period） |
| `out_of_range` | 管理员确认实际价格或输入修正价格 | 解析修正值 → INSERT trading_records |
| `missing` | 管理员补充缺失时段的数据 | 解析修正值 → INSERT trading_records |
| `duplicate` | 无需修正数据内容 | 不操作 trading_records（重复记录已被 ON CONFLICT DO NOTHING 跳过） |

**修正值解析规则**：根据 `field_name` 字段判断修正内容：
- `field_name = 'clearing_price'` → 解析为 Decimal，校验非 NaN/Inf
- `field_name = 'period'` → 解析为 int，校验范围 1-96
- `field_name = 'trading_date'` → 解析为 date，校验有效日期格式
- 多字段修正：corrected_value 使用 JSON 格式 `{"trading_date": "2025-06-01", "period": 48, "clearing_price": "350.00"}`

**修正后更新 DataImportJob 计数：**
- `success_records += 1`
- `failed_records -= 1`
- 重算 `data_completeness = success_records / total_records * 100`

### API 设计

**新增端点（独立 `/api/v1/anomalies` 路由）：**

```
GET    /api/v1/anomalies                          — 全局异常列表（跨批次）
GET    /api/v1/anomalies/{anomaly_id}             — 单条异常详情
PATCH  /api/v1/anomalies/{anomaly_id}/correct     — 修正异常数据
PATCH  /api/v1/anomalies/{anomaly_id}/confirm-normal — 标记为已确认正常
POST   /api/v1/anomalies/bulk-action              — 批量操作
```

**为什么独立路由而非嵌套在 /data-imports/{job_id}/：**
- AC#1 要求按异常类型筛选（跨批次）
- AC#2 要求按导入批次筛选（批次作为筛选条件而非路径参数）
- 异常管理页面是独立入口，不依赖特定导入任务上下文
- 保留 `GET /data-imports/{job_id}/anomalies` 用于导入结果页的关联查看（Story 2.3）

**GET /anomalies 查询参数：**
```
page: int = 1
page_size: int = 20
anomaly_type: Optional[AnomalyType] = None
status: Optional[AnomalyStatus] = "pending"  # 默认仅展示待处理
import_job_id: Optional[UUID] = None
```

**POST /anomalies/bulk-action 请求体：**
```json
{
    "anomaly_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "action": "delete"  // 或 "confirm_normal"
}
```

**PATCH /anomalies/{id}/correct 请求体：**
```json
{
    "corrected_value": "350.00"
}
```
或多字段修正：
```json
{
    "corrected_value": "{\"trading_date\": \"2025-06-01\", \"period\": 48, \"clearing_price\": \"350.00\"}"
}
```

### 前端页面设计

**异常数据管理页面布局（`AnomalyManagementView.vue`）：**

```
┌───────────────────────────────────────────────────┐
│ 异常数据管理                                        │
├───────────────────────────────────────────────────┤
│                                                     │
│  导入批次: [全部 ▼]  异常类型: [全部 ▼]              │
│  状态: [待处理 ▼]    [查询]  [重置]                  │
│                                                     │
│  ┌─ 异常统计 ─────────────────────────────────┐    │
│  │ 缺失: 18    格式错误: 5    超范围: 3    重复: 12 │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  已选中 3 项: [批量确认正常]  [批量删除]              │
│                                                     │
│  ┌──┬────┬──────┬────┬────┬──────┬────┬──────┐    │
│  │☐ │行号│异常类型│字段  │原始值│描述     │状态  │操作    │    │
│  ├──┼────┼──────┼────┼────┼──────┼────┼──────┤    │
│  │☑ │15  │缺失    │period│-   │交易日缺时段│待处理│修正 确认│    │
│  │☑ │23  │格式错误│price │abc │价格格式错误│待处理│修正 确认│    │
│  │☑ │45  │超范围  │price │9999│超出限价范围│待处理│修正 确认│    │
│  │☐ │78  │重复    │-     │-   │重复记录    │待处理│  确认  │    │
│  └──┴────┴──────┴────┴────┴──────┴────┴──────┘    │
│                              [< 1 2 3 ... 10 >]    │
└───────────────────────────────────────────────────┘
```

**UX 交互要点：**
- 筛选区使用 `a-select` 下拉 + `a-button` 查询/重置
- 统计卡片使用 `a-statistic` 展示各类型 pending 数量
- 表格使用 `a-table` 带 `rowSelection` 多选
- 异常类型列使用 `a-tag` 彩色标签（缺失=橙色、格式错误=红色、超范围=紫色、重复=蓝色）
- 状态列使用 `a-tag`（待处理=默认、已确认=绿色、已修正=绿色、已删除=灰色）
- 操作列：
  - "修正"按钮：点击弹出 `AnomalyCorrectModal`（仅 missing/format_error/out_of_range 显示）
  - "确认正常"按钮：点击 `a-popconfirm` 确认后调用 API
  - "删除"按钮：点击 `a-popconfirm` 确认后调用 API
  - 非 pending 状态行：操作按钮全部隐藏
- 批量操作栏：选中 ≥1 项时显示，使用 `a-space` 排列按钮
- 批量删除使用 `a-popconfirm` 二次确认（"确认删除选中的 N 条异常数据？"）
- 操作成功后 `a-message.success()` 提示

**修正弹窗设计（`AnomalyCorrectModal.vue`）：**

```
┌─── 修正异常数据 ──────────────────────────┐
│                                             │
│  行号: 23                                   │
│  异常类型: 格式错误                          │
│  字段: clearing_price                       │
│  原始值: abc                                │
│  描述: 出清价格格式错误: abc                 │
│                                             │
│  修正值: [____________]                      │
│  提示: 请输入正确的出清价格（元/MWh）        │
│                                             │
│              [取消]  [确认修正]              │
└─────────────────────────────────────────────┘
```

**Ant Design Vue 组件使用：**
- `a-select`：筛选下拉（导入批次、异常类型、状态）
- `a-table`：异常数据表格 + rowSelection 多选
- `a-tag`：异常类型和状态标签
- `a-statistic`：异常统计卡片
- `a-modal`：修正弹窗
- `a-input` / `a-input-number`：修正值输入
- `a-popconfirm`：确认正常 / 删除 / 批量操作确认
- `a-message`：操作反馈
- `a-button`：查询/重置/批量操作
- `a-space`：按钮组布局
- `a-descriptions`：弹窗中异常详情展示

### 现有代码基础（必须复用，禁止重写）

**直接复用（无需修改）：**
- `app/core/dependencies.py` — `get_current_active_user()`, `require_roles(["admin"])`
- `app/core/database.py` — `AsyncSession`, `get_db_session()`
- `app/core/exceptions.py` — `BusinessError`
- `app/core/ip_utils.py` — `get_client_ip()`
- `app/services/audit_service.py` — `AuditService`
- `app/repositories/base.py` — `BaseRepository`
- `app/repositories/data_import.py` — `ImportAnomalyRepository`（已有 list_by_job、get_summary_by_job）
- `app/repositories/data_import.py` — `TradingRecordRepository`（修正写入时使用 bulk_insert）
- `app/repositories/data_import.py` — `DataImportJobRepository`（更新计数时使用 update_progress）
- `app/models/data_import.py` — `ImportAnomaly`、`TradingRecord`、`DataImportJob` 模型
- `app/schemas/data_import.py` — `ImportAnomalyRead`、`AnomalyType`、`AnomalyStatus`、`ImportAnomalyListResponse`
- `web-frontend/src/api/client.ts` — Axios 实例
- `web-frontend/src/stores/auth.ts` — 认证状态
- `web-frontend/src/utils/permission.ts` — `isAdmin()`
- `web-frontend/src/types/dataImport.ts` — `ImportAnomaly`、`AnomalyType`、`AnomalyStatus`

**需要扩展的文件：**
- `app/schemas/data_import.py` — 新增 AnomalyCorrectRequest、AnomalyBulkActionRequest/Response
- `app/repositories/data_import.py` — ImportAnomalyRepository 新增 update_status、bulk_update_status、update_anomaly_value、list_all_anomalies、get_summary_all
- `app/services/data_import_service.py` — 新增修正/确认/批量操作方法
- `app/api/v1/router.py` — 注册 anomalies 路由
- `src/types/dataImport.ts` — 新增请求/响应类型
- `src/router/modules/data.routes.ts` — 新增 /data/anomalies 路由
- `src/App.vue` — 侧边栏新增"异常数据"菜单项
- `src/components/data/ImportResultSummary.vue` — 异常汇总行添加"查看详情"链接

**需要新建的文件：**

后端：
- `api-server/app/api/v1/anomalies.py`

前端：
- `web-frontend/src/api/anomaly.ts`
- `web-frontend/src/composables/useAnomalyManagement.ts`
- `web-frontend/src/views/data/AnomalyManagementView.vue`
- `web-frontend/src/components/data/AnomalyCorrectModal.vue`
- `web-frontend/src/components/data/AnomalyFilterBar.vue`

测试：
- `api-server/tests/unit/schemas/test_anomaly_schema.py`
- `api-server/tests/unit/services/test_anomaly_management_service.py`
- `api-server/tests/integration/api/test_anomalies.py`
- `web-frontend/tests/unit/composables/useAnomalyManagement.test.ts`
- `web-frontend/tests/unit/components/data/AnomalyCorrectModal.test.ts`
- `web-frontend/tests/unit/views/data/AnomalyManagementView.test.ts`

### 架构合规要求

**三层架构（强制）：**
```
API 层 (app/api/v1/anomalies.py)
  → 路由端点，注入 require_roles(["admin"])
  → 参数校验（Pydantic schema + Query params）
  → 禁止在此层写业务逻辑

Service 层 (app/services/data_import_service.py — 扩展)
  → 状态转换校验（仅 pending → 其他状态）
  → 修正值数据校验
  → 修正值写入 trading_records
  → 审计日志记录
  → 更新 DataImportJob 计数

Repository 层 (app/repositories/data_import.py — 扩展)
  → SQL 操作（查询、更新状态、批量更新）
  → 继承 BaseRepository
```

**命名规范（与 Story 2.3 一致）：**
- API 路由文件：`anomalies.py`，路由前缀 `/anomalies`
- Schema 新增：`AnomalyCorrectRequest`、`AnomalyBulkActionRequest`、`AnomalyBulkActionResponse`
- Service：扩展 `DataImportService`（不新建 Service 类，异常管理是数据导入领域的子功能）
- 前端组件：PascalCase.vue（`AnomalyCorrectModal.vue`、`AnomalyFilterBar.vue`）
- 前端 composable：`useAnomalyManagement.ts`
- 前端 API 文件：`anomaly.ts`

**错误码定义（新增）：**

| 错误码 | HTTP Status | 含义 |
|--------|-------------|------|
| `ANOMALY_NOT_FOUND` | 404 | 异常记录不存在 |
| `ANOMALY_ALREADY_PROCESSED` | 409 | 异常已处理（非 pending 状态），不可再次操作 |
| `INVALID_CORRECTED_VALUE` | 422 | 修正值校验失败（格式不合法、范围不合理） |
| `BULK_PARTIAL_FAILURE` | 409 | 批量操作中部分 ID 不存在或已处理 |

### 安全注意事项

1. **admin-only 权限**：所有异常管理操作限定 admin 角色
2. **状态转换校验**：后端强制校验状态机（仅 pending 可操作），防止前端绕过
3. **修正值校验**：后端执行完整数据校验，不信任前端传入值
4. **批量操作上限**：单次批量操作最多 100 条（防止意外全选全删）
5. **审计全覆盖**：每次操作记录完整审计日志（操作人、操作类型、操作前后值、时间、IP）
6. **SQL 注入防护**：SQLAlchemy ORM 参数化查询

### 从 Story 2.3 学到的关键经验教训

**直接适用于本 Story 的教训：**

1. **三层架构严格执行**：API 层不写业务逻辑，Service 层处理所有校验和审计
2. **审计日志在 Service 层统一处理**：使用 `audit_service.log()` 记录所有修改操作
3. **SELECT FOR UPDATE 锁**：修正/删除操作需要加锁防止并发修改同一条异常
4. **集成测试必须覆盖 403 权限**：非 admin 访问各端点均需测试
5. **前端组件禁止直接调 API**：必须通过 composable 层（`useAnomalyManagement`）
6. **Schema 测试覆盖所有新增 schema**：不留死代码
7. **错误处理使用 getErrorMessage 工具函数**：前端 API 错误展示
8. **Pydantic Literal 类型校验**：查询参数 anomaly_type 和 status 使用 Literal 类型自动校验
9. **`a-popconfirm` 二次确认**：删除和批量操作必须有确认弹窗
10. **操作后自动刷新列表**：composable 中操作成功后重新调用 loadAnomalies

### UX 设计依据

**来自 UX 规格文档的关键要求：**

- **数据异常处理原则**："数据导入后异常数据按类型分组展示，非技术人员可快速判断'这个异常要不要管'——常见异常（如节假日停市）提供一键'确认正常'"
- **情感设计原则**："从容 vs 恐慌"——异常处理应让用户感到"系统在掌控局面"，提供清晰的引导路径
- **异常处理交互原则**：
  - 温和告知，不恐慌：使用分组展示而非逐条弹出
  - 清晰说明影响范围：具体说明"哪里有问题、影响什么、怎么处理"
  - 不隐藏问题：用分级提醒（颜色+位置）而非统一弹窗
- **胜任感**：错误提示用"建议操作"而非技术错误码

### 与前后 Story 的关系

**依赖前序 Story（全部已完成）：**
- Story 1.1-1.5: 项目基础设施、认证、RBAC、绑定、数据访问控制
- Story 2.1: 电站配置向导（power_stations 表）
- Story 2.2: 省份市场规则（province_market_rules 表、价格校验范围来源）
- Story 2.3: 历史数据导入（import_anomalies 表、ImportAnomaly 模型、基础读取端点）

**为后续 Story 提供基础：**
- Story 2.5（电站出力/储能数据导入）：复用异常管理模式（同类数据导入也会产生异常）
- Epic 5（日前报价）：干净的 trading_records 数据是报价质量的基础
- Epic 7（历史回测）：修正后的数据提升回测准确性

### Git 提交历史分析

最近提交确认架构模式稳定：
```
f3addd8 Implement station storage configuration wizard and province market rules
5c50403 Implement data access control based on user roles and bindings
68e44bb Implement trader-station and operator-device binding features
```

**代码模式确认：**
- 三层架构严格执行
- 审计日志在 Service 层记录
- 前端 composable 封装所有 API 调用和状态逻辑
- 路由权限通过 `meta.roles` 定义
- Pydantic Literal 类型用于枚举值校验

### Project Structure Notes

- 无需新建 Alembic 迁移（import_anomalies 表结构完整）
- `app/api/v1/anomalies.py` 作为新路由模块独立创建
- 前端复用 `views/data/` 和 `components/data/` 子目录
- 测试新增到 `tests/unit/schemas/`、`tests/unit/services/`、`tests/integration/api/`（后端）和 `tests/unit/composables/`、`tests/unit/components/data/`、`tests/unit/views/data/`（前端）

### References

- [Source: epics/epic-2-电站配置与数据管理.md#Story 2.4] — 原始需求和 5 条验收标准
- [Source: architecture.md#Data Architecture] — Pydantic 多层校验、Repository Pattern
- [Source: architecture.md#Authentication & Security] — RBAC + admin-only 权限
- [Source: architecture.md#API & Communication Patterns] — RESTful 资源命名、统一错误响应格式
- [Source: architecture.md#Implementation Patterns] — 三层架构、命名规范、反模式
- [Source: architecture.md#Cross-Cutting Concerns#1] — 审计日志（操作记录）
- [Source: ux-design-specification.md#旅程流程3] — 异常数据按类型分组展示，节假日停市一键确认
- [Source: ux-design-specification.md#异常处理交互原则] — 温和告知不恐慌、清晰说明影响范围
- [Source: ux-design-specification.md#情感设计] — 从容 vs 恐慌、胜任感
- [Source: 2-3-historical-data-import.md] — 前序 Story 完成记录、代码模式、审查教训
- [Source: 2-3-historical-data-import.md#Review Follow-ups] — Schema 测试覆盖、403 权限测试、SELECT FOR UPDATE 锁
- [Source: project-context.md#Framework-Specific Rules] — FastAPI 三层架构、Vue Composition API
- [Source: project-context.md#Testing Rules] — Pytest 异步测试、Vitest 组件测试
- [Source: project-context.md#Code Quality] — 命名规范全链路统一

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Change Log

### File List
