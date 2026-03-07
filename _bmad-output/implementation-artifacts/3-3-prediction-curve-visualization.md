# Story 3.3: 功率预测曲线可视化

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 交易员（李娜）,
I want 查看指定电站的96时段功率预测曲线及置信区间，并切换不同预测模型的结果,
so that 我能直观了解明天的发电预测情况，为报价决策提供参考。

## Acceptance Criteria

1. **AC1 - 96时段预测曲线展示**: Given 交易员已登录并选择一个已绑定的电站 | When 进入功率预测页面 | Then 展示该电站的96时段功率预测曲线图，横轴为时段（1-96），纵轴为预测功率（kW），同时展示置信区间上下限（填充区域）
2. **AC2 - 模型切换**: Given 系统配置了多个预测模型（MVP仅1个自有模型） | When 交易员在模型选择器中切换模型 | Then 曲线图切换为所选模型的预测结果
3. **AC3 - 性能与加载体验**: Given 交易员打开预测曲线页面 | When 页面加载完成 | Then 预测数据加载时间<5秒（P95，10并发），加载过程中显示骨架屏
4. **AC4 - 无数据状态处理**: Given 预测数据尚未生成（模型未执行或拉取失败） | When 交易员访问预测页面 | Then 页面显示"暂无预测数据"提示及最后成功拉取的时间戳

## Tasks / Subtasks

### 后端任务

- [ ] Task 1: 后端API扩展 — 预测模型列表查询（交易员可用） (AC: #2)
  - [ ] 1.1 在 `api/v1/predictions.py` 新增 `GET /prediction-models/by-station/{station_id}` 端点（trader + admin 可访问），返回指定电站已配置且 `is_active=True` 的预测模型列表（id, model_name, model_type, status）
  - [ ] 1.2 在 `PredictionModelRepository` 新增 `get_active_by_station(station_id)` 方法
  - [ ] 1.3 确保端点执行 DataAccessContext 权限校验（复用 Story 3.2 H1 修复模式）

### 前端任务

- [ ] Task 2: 图表库技术方案落地 (AC: #1)
  - [ ] 2.1 移除 `@ant-design/charts`（React库，Vue 3不兼容），安装 `@antv/g2`（G2 v5，框架无关的底层渲染引擎）
  - [ ] 2.2 创建 `src/composables/useG2Chart.ts` 通用 composable：封装 G2 Chart 实例的创建、更新、销毁生命周期管理（onMounted 创建、watch 数据更新、onUnmounted 销毁）
  - [ ] 2.3 在 `package.json` 中确认 `@antv/g2` 版本为 v5.x 最新稳定版

- [ ] Task 3: TypeScript 类型扩展 (AC: #1, #2, #4)
  - [ ] 3.1 在 `src/types/prediction.ts` 新增 `PredictionChartDataPoint` 类型：`{ period: number, time_label: string, predicted_power_kw: number, confidence_upper_kw: number, confidence_lower_kw: number }`
  - [ ] 3.2 新增 `PredictionModelOption` 类型：`{ id: string, model_name: string, model_type: ModelType, status: ModelStatus }`
  - [ ] 3.3 新增 `PredictionModelListResponse` 类型：`{ items: PredictionModelOption[], total: number }`

- [ ] Task 4: API 客户端扩展 (AC: #1, #2)
  - [ ] 4.1 在 `src/api/prediction.ts` 新增 `getModelsByStation(stationId: string): Promise<PredictionModelListResponse>` 方法
  - [ ] 4.2 确认已有的 `getStationPredictions(stationId, predictionDate, modelId?)` 方法满足需求

- [ ] Task 5: 创建 usePredictionCurve composable (AC: #1, #2, #3, #4)
  - [ ] 5.1 创建 `src/composables/usePredictionCurve.ts`
  - [ ] 5.2 状态管理：`loading`(ref<boolean>)、`predictions`(ref<PowerPrediction[]>)、`models`(ref<PredictionModelOption[]>)、`selectedModelId`(ref<string | null>)、`selectedDate`(ref<string>，默认明天)、`lastFetchTime`(ref<string | null>)、`hasData`(computed<boolean>)
  - [ ] 5.3 实现 `fetchModels(stationId)` — 加载该电站的可用预测模型列表，默认选中第一个 status=running 的模型
  - [ ] 5.4 实现 `fetchPredictions(stationId, date, modelId)` — 调用 `predictionApi.getStationPredictions()`，失败时设 predictions 为空数组
  - [ ] 5.5 实现 `chartData` computed — 将 `PowerPrediction[]` 转换为 `PredictionChartDataPoint[]`（添加 time_label: period→HH:MM 映射，如 period 1→"00:00"、period 4→"00:45"、period 33→"08:00"）
  - [ ] 5.6 实现 `switchModel(modelId)` — 切换选中模型并重新拉取预测数据
  - [ ] 5.7 实现 `switchDate(date)` — 切换预测日期并重新拉取数据
  - [ ] 5.8 watch `stationId` 变化自动重新加载模型列表和预测数据

- [ ] Task 6: 创建 PowerForecastChart 组件 (AC: #1, #3)
  - [ ] 6.1 创建 `src/components/charts/PowerForecastChart.vue`
  - [ ] 6.2 Props: `data: PredictionChartDataPoint[]`、`loading: boolean`、`height?: number`（默认400）
  - [ ] 6.3 使用 G2 v5 渲染折线图（预测功率曲线）+ Area mark（置信区间填充区域，半透明蓝色 `rgba(24,144,255,0.15)`）
  - [ ] 6.4 X轴配置：字段 `time_label`，标签间隔显示（每4个时段=1小时显示一个刻度），标题"时段"
  - [ ] 6.5 Y轴配置：字段 `predicted_power_kw`，标题"预测功率 (kW)"，自动刻度
  - [ ] 6.6 Tooltip 配置：hover 显示"时段 X (HH:MM) | 预测功率: X kW | 上限: X kW | 下限: X kW"
  - [ ] 6.7 loading 状态显示 `a-skeleton` 骨架屏（与 UX 规范 2s-10s 加载策略一致）
  - [ ] 6.8 空数据状态显示 `a-empty` + description="暂无预测数据"
  - [ ] 6.9 图表颜色语义：预测曲线使用 `#1890FF`（Ant Design 主色），置信区间填充使用 `rgba(24,144,255,0.15)`
  - [ ] 6.10 图表响应式：autoFit 适配容器宽度

- [ ] Task 7: 创建 PredictionCurveView 页面 (AC: #1, #2, #3, #4)
  - [ ] 7.1 创建 `src/views/data/PredictionCurveView.vue`
  - [ ] 7.2 页面布局（使用 `a-card`）：
    - 顶部工具栏：电站选择器（`a-select`，数据源复用现有电站列表）+ 模型选择器（`a-select`）+ 日期选择器（`a-date-picker`，默认明天）
    - 中央区域：`PowerForecastChart` 组件
    - 底部信息栏：数据新鲜度指示（最后成功拉取时间 + 数据状态 Tag）
  - [ ] 7.3 电站选择器：仅展示当前用户已绑定的电站（复用现有 stationApi 或 Pinia store）
  - [ ] 7.4 模型选择器：展示该电站已配置的预测模型（从 Task 1 API 获取），默认选中第一个 running 模型
  - [ ] 7.5 日期选择器：`a-date-picker`，默认值明天（`dayjs().add(1, 'day')`），用户可切换查看历史日期预测
  - [ ] 7.6 无数据状态（AC4）：当 `hasData=false` 时，图表区域显示 `a-result` status="info" + "暂无预测数据" + 最后成功拉取时间
  - [ ] 7.7 数据新鲜度 Badge：最后拉取时间距今 < 24h 显示绿色 Tag "数据已更新"，> 24h 显示橙色 Tag "数据可能过期"

- [ ] Task 8: 路由与菜单注册 (AC: #1)
  - [ ] 8.1 在 `src/router/modules/data.routes.ts` 新增路由：`{ path: '/data/prediction-curve', name: 'PredictionCurve', component: () => import('@/views/data/PredictionCurveView.vue'), meta: { requiresAuth: true, roles: ['admin', 'trader'] } }`
  - [ ] 8.2 在 `src/App.vue` 侧边栏菜单中新增"预测曲线"菜单项（在"预测模型"菜单项下方），图标使用 `LineChartOutlined`
  - [ ] 8.3 菜单 key 映射：`'/data/prediction-curve': 'prediction-curve'`

### 测试任务

- [ ] Task 9: 后端单元测试 (AC: #2)
  - [ ] 9.1 Repository 测试：`get_active_by_station` 返回正确模型列表
  - [ ] 9.2 API 集成测试：`GET /prediction-models/by-station/{station_id}` 权限校验和响应格式

- [ ] Task 10: 前端 Composable 测试 (AC: #1, #2, #4)
  - [ ] 10.1 `usePredictionCurve` 测试：fetchModels 调用 API 并设置 models、fetchPredictions 设置 predictions、switchModel 切换模型并重新获取、chartData computed 正确转换 period→time_label
  - [ ] 10.2 空数据场景测试：API 返回空列表时 hasData=false

- [ ] Task 11: 前端组件测试 (AC: #1, #3, #4)
  - [ ] 11.1 `PowerForecastChart` 测试：loading 状态显示 skeleton、空数据显示 empty、有数据时挂载 chart 容器 div
  - [ ] 11.2 `PredictionCurveView` 测试：电站选择器渲染、模型选择器渲染、日期选择器默认值为明天、无数据时显示 a-result

## Dev Notes

### 核心设计决策

1. **图表库选型变更**: 架构文档指定 `@ant-design/charts`（基于 G2 v5），但该库是 React 专用组件库，不兼容 Vue 3。**解决方案**：移除 `@ant-design/charts`，直接使用 `@antv/g2`（G2 v5底层引擎，框架无关）。G2 v5 提供纯 JS API（`new Chart({ container, ... })`），可在 Vue 3 的 `onMounted` 中创建实例、`watch` 中更新数据、`onUnmounted` 中销毁。UX 设计不受影响——折线图+区域填充的视觉效果完全一致。

2. **PowerForecastChart 组件作为 L3 领域组件**: UX 规范定义了 PowerForecastChart 为6个核心 L3 自定义组件之一（P1优先级），支持三种状态："仅预测"（本 Story）、"预测+实际"（回测场景）、"偏差高亮"（后续迭代）。本 Story 仅实现"仅预测"状态。

3. **置信区间可视化**: 使用 G2 v5 的 Area mark 渲染置信区间（上限-下限之间的填充区域），颜色为主色调半透明 `rgba(24,144,255,0.15)`，叠加 Line mark 渲染预测功率主曲线。

4. **时段→时间映射**: 96时段为15分钟间隔。Period 1 = 00:00-00:15, Period 96 = 23:45-24:00。X轴显示 time_label（HH:MM格式），Tooltip 同时显示时段号和时间。映射公式：`HH = Math.floor((period - 1) * 15 / 60)`、`MM = ((period - 1) * 15) % 60`。

5. **交易员可访问**: 本页面面向交易员（admin + trader 角色），非管理员专属。电站选择器仅展示用户已绑定的电站。

6. **日期默认值**: 默认展示明天（T+1日）的预测数据，这与 Story 3.2 的拉取策略一致——每日拉取明天的96时段预测。用户可切换到其他日期查看历史预测。

### 架构约束与模式

**三层架构**（与 Story 3.1/3.2 一致）:
- API层 → Service层 → Repository层
- 本 Story 后端变更量小：仅新增1个查询端点 + 1个 Repository 方法

**前端组件层级**:
- L1: Ant Design Vue 原生组件（a-select, a-date-picker, a-card, a-skeleton, a-empty, a-tag, a-result）
- L2: 无新增
- L3: PowerForecastChart（G2 v5 封装）

**DataAccessContext 权限模式**（Story 3.2 H1 修复经验）:
```python
# 正确模式：所有交易员可见的电站数据端点必须校验权限
@router.get("/prediction-models/by-station/{station_id}")
async def get_models_by_station(
    station_id: uuid.UUID,
    access_context: DataAccessContext = Depends(get_data_access_context),
    session: AsyncSession = Depends(get_session),
):
    station_service = StationService(session)
    await station_service.get_station_for_user(station_id, access_context)
    # 然后查询模型...
```

**G2 v5 Vue 3 集成模式**:
```typescript
// useG2Chart.ts composable 模式
import { Chart } from '@antv/g2'

export function useG2Chart(containerRef: Ref<HTMLElement | null>) {
  let chart: Chart | null = null

  onMounted(() => {
    if (containerRef.value) {
      chart = new Chart({ container: containerRef.value, autoFit: true })
      // 初始化图表配置...
      chart.render()
    }
  })

  function updateData(data: any[]) {
    if (chart) {
      chart.changeData(data)
    }
  }

  onUnmounted(() => {
    chart?.destroy()
    chart = null
  })

  return { updateData }
}
```

**前端测试规范（从 Story 3.2 经验提炼）**:
- `window.matchMedia` mock 必须添加（ant-design-vue 依赖）
- `a-card`/`a-row`/`a-col` 需要 `{ template: '<div><slot /></div>' }` 形式的 stub
- G2 Chart 在测试环境中 mock 掉（jsdom 不支持 Canvas），仅验证容器 div 渲染
- composable 测试 mock API 调用，验证状态变化

**period→time_label 转换工具函数**:
```typescript
// 可放在 src/utils/period.ts 或直接在 composable 内
export function periodToTimeLabel(period: number): string {
  const totalMinutes = (period - 1) * 15
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
}
```

### 关键文件路径

**必须新建的文件**:
- `web-frontend/src/composables/useG2Chart.ts` — G2 Chart 生命周期管理 composable
- `web-frontend/src/composables/usePredictionCurve.ts` — 预测曲线数据管理 composable
- `web-frontend/src/components/charts/PowerForecastChart.vue` — 功率预测曲线 L3 组件
- `web-frontend/src/views/data/PredictionCurveView.vue` — 预测曲线页面

**必须修改的现有文件**:
- `web-frontend/package.json` — 移除 `@ant-design/charts`、添加 `@antv/g2`
- `web-frontend/src/types/prediction.ts` — 新增 PredictionChartDataPoint、PredictionModelOption 类型
- `web-frontend/src/api/prediction.ts` — 新增 getModelsByStation 方法
- `web-frontend/src/router/modules/data.routes.ts` — 新增预测曲线路由
- `web-frontend/src/App.vue` — 侧边栏新增预测曲线菜单项
- `api-server/app/api/v1/predictions.py` — 新增 by-station 端点
- `api-server/app/repositories/prediction.py` — 新增 get_active_by_station 方法

**测试文件**:
- `web-frontend/tests/unit/composables/usePredictionCurve.test.ts` — 新建
- `web-frontend/tests/unit/components/charts/PowerForecastChart.test.ts` — 新建
- `web-frontend/tests/unit/views/data/PredictionCurveView.test.ts` — 新建
- `api-server/tests/integration/api/test_predictions.py` — 扩展

### 前一故事(3-2)关键经验

1. **DataAccessContext 权限校验**: 所有涉及电站数据的交易员端点必须执行权限验证（Story 3.2 H1 修复项），防止 IDOR 攻击
2. **前端 CRUD 返回 boolean**: composable 中操作方法返回 boolean 表示成功/失败
3. **window.matchMedia mock**: 前端测试必须添加（ant-design-vue 依赖）
4. **template stubs**: a-card/a-row/a-col 需要 `{ template: '<div><slot /></div>' }` 形式的 stub
5. **操作后自动刷新**: 切换操作成功后自动重新获取数据

### 技术栈版本

- Python 3.12, FastAPI 0.133.x, SQLAlchemy 2.0.x (async, asyncpg), Pydantic 2.x
- Vue 3.5.x, TypeScript 5.x, Vite 7.x, Pinia 3.0.x, Ant Design Vue 4.2.x
- **@antv/g2 v5.x**（替代 @ant-design/charts，底层引擎相同）
- PostgreSQL 18.x + TimescaleDB 2.23.x
- Pytest (pytest-asyncio), Vitest 4.0.x
- dayjs（日期处理，Ant Design Vue 内置依赖）

### 与后续 Story 的关系

- **Epic 5 Story 5.1（多电站概览）**: 将复用 PowerForecastChart 组件在电站卡片中展示迷你预测概览
- **Epic 5 Story 5.2（96时段价格调整）**: 交易工作台将在 PowerForecastChart 旁边展示电价曲线，需要 PowerForecastChart 支持双Y轴叠加（本 Story 不实现，但组件设计需预留扩展空间）
- **Epic 7（历史回测）**: 将使用 PowerForecastChart 的"预测+实际"状态展示回测对比
- **useG2Chart composable**: 将被其他图表组件（RevenueWaterfall、PriceHeatmap 等）复用

### UX 设计要点

- **骨架屏加载**（AC3）: 2s-10s 加载时段使用 `a-skeleton` 骨架屏占位（UX规范 Loading 策略），保持图表区域结构
- **数据新鲜度指示**: Grafana 风格，显示最后拉取时间 + 颜色 Tag（<24h 绿色、>24h 橙色）
- **颜色语义**: 预测曲线 `#1890FF`（Ant Design 主蓝）、置信区间填充 `rgba(24,144,255,0.15)`（半透明蓝）
- **时段标签**: X轴每小时显示一个刻度（每4个时段），避免标签拥挤
- **Tooltip**: 显示完整信息（时段号、时间、预测值、上限、下限），使用自然语言
- **空状态**: 使用 `a-result` status="info" 显示"暂无预测数据"，附带最后成功拉取时间戳
- **专业感设计**: 避免花哨动效，追求"稳重、专业、数据驱动"（UX 情感设计原则1）

### Project Structure Notes

- 新建 `src/components/charts/` 目录作为图表组件统一存放位置
- PowerForecastChart 作为第一个 L3 图表组件，建立图表组件开发模式
- useG2Chart composable 建立 G2 v5 集成标准模式，后续图表组件复用
- 路由 path 使用 `/data/prediction-curve`（与 `/data/prediction-models` 同级）

### References

- [Source: _bmad-output/planning-artifacts/epics/epic-3-功率预测与数据可视化.md#Story 3.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Technology Stack - @ant-design/charts 替代说明]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#PowerForecastChart — 功率预测对比曲线]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Implementation Strategy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Loading 策略]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#颜色语义系统]
- [Source: _bmad-output/planning-artifacts/prd/functional-requirements.md#FR1 FR2]
- [Source: _bmad-output/planning-artifacts/prd/non-functional-requirements.md#NFR2 预测曲线加载<5秒]
- [Source: _bmad-output/implementation-artifacts/3-2-prediction-data-auto-fetch.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/3-2-prediction-data-auto-fetch.md#Senior Developer Review]
- [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
