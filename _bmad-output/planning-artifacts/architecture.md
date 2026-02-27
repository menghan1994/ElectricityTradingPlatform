---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-26'
inputDocuments:
  - product-brief-ElectricityTradingPlatform-2026-02-24.md
  - prd/index.md
  - prd/executive-summary.md
  - prd/functional-requirements.md
  - prd/non-functional-requirements.md
  - prd/domain-specific-requirements.md
  - prd/saas-b2b-specific-requirements.md
  - prd/product-scope-phased-development.md
  - ux-design-specification.md
  - research/technical-multi-agent-framework-research-2026-02-25/technology-stack-analysis.md
  - research/technical-multi-agent-framework-research-2026-02-25/architectural-patterns-and-design.md
  - research/technical-multi-agent-framework-research-2026-02-25/technical-research-recommendations.md
workflowType: 'architecture'
project_name: 'ElectricityTradingPlatform'
user_name: 'hmeng'
date: '2026-02-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

共58条功能需求，分布在10个核心模块中。架构层面需要重点支撑的模块包括：

- **多智能体协作引擎**（FR54-FR58）：LangGraph层级式Supervisor编排5个Agent协作完成端到端96时段报价建议生成，需支持中断-恢复（Human-in-the-Loop）、协作失败降级为规则引擎、全链路决策记录
- **日前报价决策**（FR5-FR10, FR50-FR51）：AI建议生成→交易员审核/微调/确认的核心工作流，含负电价识别预警和储能联合优化
- **储能调度管理**（FR38-FR46）：96时段充放电计划生成（规则策略）、设备约束硬校验（SOC/倍率）、调度指令生成→运维员确认/拒绝→执行反馈闭环
- **历史回测系统**（FR11-FR16）：用真实历史数据运行AI策略回测，含收益归因分析和PDF报告导出——这是MVP核心卖点
- **审计与合规**（FR34-FR37）：Agent级决策链路完整记录，审计日志≥3年不可篡改
- **数据管理与导入**（FR23-FR29）：引导式配置向导、批量数据导入+质量校验+异常处理闭环（导入→解析→校验→分类标记→人工确认→入库）、外部API接入

**Non-Functional Requirements:**

共33条非功能需求，驱动架构决策的关键约束：

| 分类 | 关键约束 | 架构影响 |
|------|---------|---------|
| **性能** | 96时段报价生成<30秒（NFR1）；储能计划<30秒（NFR20）；页面加载<3-5秒；1年回测<10分钟（NFR3） | Agent并行执行策略、缓存机制、前端懒加载、回测引擎批处理架构 |
| **安全** | TLS 1.2+传输（NFR6）；AES-256存储加密（NFR7）；数据不出境（NFR9）；Prompt注入防护（NFR32） | 全链路加密、本地部署架构、Agent输入输出安全过滤层 |
| **可扩展性** | 单实例≥20电站（NFR11）；≥10并发用户（NFR5）；≥3年历史数据（NFR13）；≥10台储能设备（NFR22） | 数据分区策略、连接池管理、时序数据增长建模 |
| **可靠性** | 交易日可用性≥99.5%（NFR14）；Agent协作成功率≥95%（NFR28）；设备约束违反率0%（NFR24）；RTO≤4h/RPO≤1h（NFR26） | 降级机制、健康检查、自动备份、约束硬校验层、属性测试覆盖 |
| **集成** | 预测模型标准化API（NFR17）；外部数据源30秒切换缓存（NFR18）；储能EMS标准模板（NFR25） | 适配器模式、缓存降级策略、数据模板抽象 |
| **多Agent** | Token消耗上限20K/次（NFR29）；可观测性100%链路记录（NFR30）；LLM热切换仅改配置（NFR31）；Agent输出质量基线监控（NFR33） | Token限制中间件、Langfuse集成、模型配置抽象、质量评估管道子系统 |

**UX对架构的影响：**

| UX需求 | 架构影响 |
|--------|---------|
| Agent协作进度实时展示（步骤条） | LangGraph节点完成事件 → WebSocket/SSE推送 → 前端实时更新，需定义事件粒度和推送频率 |
| 30秒等待期的有意义设计 | Agent执行过程中每个节点需发射状态事件（Agent名称/状态/耗时） |
| 多电站上下文快速切换 | 前端需维护多电站并行状态（Pinia store结构设计），切换时保持各自独立的报价/储能/Agent执行状态 |
| PDF回测报告导出（含图表） | 需要服务端PDF渲染方案（Puppeteer/Playwright或专用PDF库），包含KPI卡片、瀑布图、折线图 |
| 渐进式Agent决策链路展开 | Agent输出需区分面向用户的自然语言摘要字段和面向开发者的原始日志 |
| 数据新鲜度指示 | 每个数据面板需关联数据更新时间戳，超期自动变更视觉状态 |

**Scale & Complexity:**

- 主要技术领域：全栈（Full-Stack）— Vue 3前端 + Python FastAPI后端 + LangGraph多Agent引擎 + PostgreSQL数据层
- 复杂度级别：**企业级（Enterprise）**
- 预估架构组件数：~18个核心组件/服务

### Technical Constraints & Dependencies

**硬性约束：**
1. **部署模式**：本地/私有云部署（国资企业不接受公有云SaaS），Docker Compose（MVP）→ K8s（生产级）
2. **数据主权**：数据存储和处理100%境内完成，无任何境外数据传输
3. **前端框架**：Vue 3（国产软件审计合规要求，不可选React）
4. **Agent框架**：LangGraph v1.0+（MIT开源，支持完全私有化部署）
5. **可观测性**：Langfuse自托管（替代LangSmith，满足数据本地化要求）
6. **审计日志**：追加写入模式，不可修改/删除，保留≥3年
7. **离线/半离线更新**：产品升级和模型更新需适配离线/半离线环境（影响LLM模型分发、Agent配置热更新、前端静态资源更新的架构设计）

**技术依赖：**
- LangGraph v1.0+（Agent编排）+ LangChain（LLM抽象层）
- PostgreSQL（业务数据 + LangGraph检查点 + TimescaleDB扩展）
- Ollama/vLLM（本地LLM部署）
- Langfuse（Agent可观测性自托管）
- FastAPI（后端API）
- Vue 3 + Ant Design Vue 4.x + AntV G2Plot（前端）
- PDF渲染引擎（服务端图表渲染，Puppeteer/WeasyPrint等待选）

### Cross-Cutting Concerns Identified

1. **审计与可追溯性**：所有模块的关键操作均需记录审计日志（时间戳+操作人+操作内容+变更前后值），Agent决策链路需完整记录每个Agent的输入/输出/状态/耗时/LLM模型
2. **降级与容错**：三层降级策略——Agent协作失败→规则引擎；储能引擎异常→无储能模式报价；外部数据源异常→缓存数据（30秒切换，缓存有效期≤24h）
3. **安全与加密**：传输层TLS 1.2+ + 存储层AES-256字段级加密 + Agent输入输出安全过滤（防Prompt注入）+ 强密码策略 + 会话超时
4. **可观测性**：Langfuse全链路追踪（100% Agent调用链路记录），Token成本归因，性能监控，Agent输出质量基线监控
5. **实时通信架构**：WebSocket/SSE事件推送机制贯穿前后端——Agent协作进度推送、储能调度指令下发（NFR21 <10秒延迟）、数据新鲜度状态同步。需定义统一的事件协议和推送频率策略
6. **数据新鲜度管控**：电价数据超24小时自动预警并在UI显著提示，公开市场数据每日报价前必须更新
7. **多省份规则适配**：规则引擎需支持深度抽象——不仅是参数配置差异，还包括偏差考核公式等完全不同的计算逻辑。架构上需定义：配置驱动（参数）+ 插件化（计算逻辑）的混合方案
8. **设备安全约束**：储能调度指令的SOC上下限、充放电倍率等约束硬校验，违反率必须为0%（NFR24），超限指令自动拦截。需属性测试/模糊测试覆盖边界条件
9. **离线/半离线更新分发**：LLM模型文件分发、Agent配置版本管理、前端静态资源更新包、规则引擎插件更新——均需适配无公网或受限公网环境
10. **多Agent系统可测试性**：Agent代码结构需预留依赖注入点、工具Mock接口、状态快照对比机制，支持LangGraph推荐的两层测试策略（单节点单元测试 + 完整图集成测试）
11. **Agent输出质量评估管道**：NFR33要求月度评估Agent输出质量并偏离告警——需设计评估数据集管理、评估指标定义、自动评估脚本、告警集成的子系统架构

### Key Architecture Decision Points（待后续步骤决策）

以下在上下文分析阶段识别但需在后续架构决策步骤中明确的关键问题：

1. **回测引擎架构模式**：是使用LangGraph重放完整Agent决策流程（高保真但计算密集），还是构建独立的简化回测引擎（高效但可能偏离实际Agent行为）？NFR3要求1年回测<10分钟
2. **省份规则引擎抽象深度**：纯配置驱动 vs 配置+插件化混合 vs 嵌入式DSL
3. **PostgreSQL身兼多职的评估**：MVP阶段PostgreSQL同时承担业务数据、LangGraph检查点、TimescaleDB时序数据可以接受，但需标记为Phase 2的架构评估项——特别是3年×20电站×96时段粒度的时序数据增长模型
4. **PDF报告渲染方案选型**：服务端无头浏览器（Puppeteer/Playwright）vs 专用PDF库（WeasyPrint/ReportLab）vs 前端生成（html2canvas+jsPDF）
5. **前端状态管理架构**：多电站并行状态的Pinia store结构设计

## Starter Template Evaluation

### Primary Technology Domain

全栈（Full-Stack）应用：Vue 3 前端 + Python FastAPI 后端 + LangGraph 多 Agent 引擎 + PostgreSQL 数据层。前后端分离架构，通过 REST API + WebSocket 通信。

### Technical Preferences Confirmed

- **前端**：Vue 3 + TypeScript（国产软件审计合规要求）
- **后端**：Python 3.12 + FastAPI（异步高性能）
- **Agent**：LangGraph + LangChain（模型无关架构）
- **数据库**：PostgreSQL + TimescaleDB
- **部署**：Docker Compose（MVP）→ K8s（生产级），本地/私有云
- **LLM**：本地部署（Ollama→vLLM）+ 国产商业 API 备选，试点环境有 GPU

### Starter Approach: Custom Scaffold（自定义脚手架）

**为什么不使用现成 starter template：**

本项目横跨 Vue 3 前端 + Python FastAPI 后端 + LangGraph Agent 引擎三个独立技术域，没有任何现成的 starter template 能同时覆盖这三层。市场上的 starter 要么是纯前端（Vite + Vue 模板），要么是纯后端（FastAPI 模板），要么是纯 Agent（LangGraph 模板）。因此采用分层脚手架策略：每层使用各自生态的标准初始化工具，然后通过 Docker Compose 统一编排。

### Technology Stack（版本已验证 2026-02-26）

#### 前端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.5.x | 稳定版（3.6 Vapor Mode 仍在 beta，MVP 不采用） |
| Vite | 7.x | 当前稳定构建工具（Vite 8 Rolldown 仍在 beta） |
| TypeScript | 5.x | Vue 3 + Vite 默认支持 |
| Pinia | 3.0.x | Vue 3 官方状态管理（v3 去掉 Vue 2 包袱） |
| Vue Router | 5.0.x | 从 v4 无破坏性升级，新增 View Transition API |
| Ant Design Vue | 4.2.x | 企业级 UI 组件库 |
| @ant-design/charts | latest（基于 G2 v5） | 替代已停止维护的 G2Plot，与 Ant Design 视觉一致 |
| Vitest | 4.0.x | Vue 生态标配测试框架，内置 Playwright Traces |

**初始化命令：**

```bash
npm create vite@latest web-frontend -- --template vue-ts
cd web-frontend
npm install pinia@3 vue-router@5 ant-design-vue@4 @ant-design/charts
npm install -D vitest@4 @vue/test-utils playwright
```

**注意：UX 规格中原选 AntV G2Plot 已进入维护模式，改用 @ant-design/charts（底层 G2 v5），API 更现代且与 Ant Design 视觉统一，不影响 UX 设计本身。**

#### 后端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.12 | FastAPI 推荐版本，LangChain 要求 ≥3.10 |
| FastAPI | 0.133.x | 高性能异步 API 框架，原生支持 WebSocket |
| SQLAlchemy | 2.0.x | Python 生态最成熟 ORM，支持异步（asyncpg） |
| Alembic | 1.18.x | SQLAlchemy 配套数据库迁移工具 |
| Pydantic | 2.x | FastAPI 原生集成，数据校验和序列化 |
| Celery | 5.6.x | 异步任务队列（回测、PDF 生成、批量导入） |
| Redis | 7.x | Celery broker + 应用级缓存（外部数据源降级） |
| Pytest | latest | Python 标准测试框架 |

**初始化命令：**

```bash
mkdir api-server && cd api-server
python -m venv .venv && source .venv/bin/activate
pip install fastapi[standard] sqlalchemy[asyncio] asyncpg alembic pydantic celery[redis] redis
pip install pytest pytest-asyncio httpx  # 测试依赖
```

#### AI/Agent 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| LangGraph | 1.0.x | Agent 编排核心，v1.0 里程碑 |
| LangChain | 1.2.x | LLM 抽象层，模型无关架构 |
| langchain-openai | latest | OpenAI 兼容接口（同时适配 Ollama/vLLM/商业 API） |
| langgraph-checkpoint-postgres | latest | Agent 状态检查点持久化 |
| Langfuse Python SDK | 3.14.x | Agent 可观测性集成 |

**初始化命令：**

```bash
pip install langgraph langchain langchain-openai langgraph-checkpoint-postgres langfuse
```

#### LLM 部署方案

**分阶段策略：MVP Ollama → 生产 vLLM，国产商业 API 备选**

| 阶段 | 推理引擎 | 模型 | 适用场景 |
|------|---------|------|---------|
| MVP 开发期（前4周） | Ollama 0.17.x | Qwen3 8B Q4 量化 | 快速启动，1-2 并发足够 |
| MVP 试点部署 | vLLM latest | Qwen3 8B | 多交易员并发，持续批处理满足30秒约束 |
| 备选/降级 | 国产商业 API | 通义千问 qwen-max 等 | GPU 不可用或模型质量不足时的降级方案 |

**架构关键设计：** 所有 LLM 调用统一通过 LangChain `ChatOpenAI` 的 OpenAI 兼容接口，切换推理引擎仅需修改配置文件中的 `base_url` 和 `model`，零代码改动（满足 NFR31）。

```python
# 配置示例（环境变量或配置文件）
# Ollama（开发）
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen3:8b

# vLLM（生产）
LLM_BASE_URL=http://vllm:8000/v1
LLM_MODEL=qwen3-8b

# 国产商业API（备选）
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
LLM_API_KEY=sk-xxx
```

**并发推理需求分析：**
- 单次报价生成：6-8 次 LLM 调用（预测子图3次并行 + 策略/储能/风控串行 + 协调2次）
- 多交易员并行（NFR5 ≥10并发）：极端情况 10-15 个并发 LLM 请求
- Ollama 串行瓶颈在多并发下会导致排队，vLLM 的持续批处理可在同等 GPU 上支撑更高并发
- 试点部署环境已确认有 GPU，满足本地 LLM 推理的硬件要求

**不同 Agent 可使用不同模型（混合部署）：**
- 协调 Agent / 策略 Agent / 风控 Agent：使用强推理模型（qwen-max 或 Qwen3 8B）
- 预测数据预处理 Agent：使用轻量模型（Qwen3 4B 或规则引擎替代）
- 配置通过 Agent 级别的 LLM 配置项实现，每个 Agent 独立指定模型

#### 数据层

| 技术 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 18.x | 业务数据 + LangGraph 检查点 |
| TimescaleDB | 2.23.x | PostgreSQL 扩展，96时段时序数据优化，UUIDv7 压缩节省30%+ 存储 |

#### 部署与工具链

| 技术 | 说明 |
|------|------|
| Docker Compose | MVP 单机部署编排 |
| Nginx | 反向代理 + TLS 终止 + 前端静态资源服务 |
| Playwright | 双用途——PDF 报告服务端渲染 + E2E 测试（Vitest 4.0 已内置集成） |
| Langfuse | v3.x 自托管（Docker tag `langfuse/langfuse:3`） |

### Docker Compose 服务清单（MVP）

```yaml
# docker-compose.yml 服务清单
services:
  web-frontend:      # Vue 3 + Nginx（静态资源 + 反向代理）
  api-server:        # FastAPI 应用服务
  celery-worker:     # Celery 异步任务处理（回测/PDF/数据导入）
  langgraph-app:     # LangGraph Agent 应用
  postgresql:        # 业务数据 + 检查点 + TimescaleDB
  redis:             # Celery broker + 应用缓存
  ollama:            # 本地 LLM 服务（开发期，GPU 环境）
  langfuse:          # Agent 可观测性平台
```

**Note:** 项目初始化使用以上命令应作为第一个实现 Story。vLLM 替换 Ollama 在试点部署阶段执行，仅需替换 Docker Compose 中的 `ollama` 服务为 `vllm` 服务并修改 LLM 配置。

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. 数据建模：SQLAlchemy 声明式映射 + Repository Pattern
2. 认证方式：JWT 双 Token（Access + Refresh）
3. 授权模式：RBAC + 资源级权限（用户-电站关联）
4. API 风格：RESTful + OpenAPI 自动文档
5. 实时通信：SSE 统一推送
6. Pinia Store：按功能模块拆分 + 电站 ID 索引
7. 回测引擎：混合模式（快速回放 + 深度重跑）
8. 省份规则引擎：配置 + 插件化混合

**Important Decisions (Shape Architecture):**
1. 时序数据：TimescaleDB 超表 + 连续聚合
2. 数据校验：Pydantic 多层校验
3. 缓存策略：混合模式（Cache-Aside + Read-Through）
4. Agent 安全：输入输出过滤层
5. 数据加密：传输 TLS + 字段级 AES-256
6. PostgreSQL 多 Schema 隔离
7. PDF 渲染：Playwright 服务端渲染

**Deferred Decisions (Post-MVP):**
1. CI/CD 平台选型（Phase 2 引入 GitLab CI）
2. K8s 编排（Phase 3）
3. ELK/Prometheus 监控栈（Phase 2 按需引入）
4. PostgreSQL 多实例拆分（Phase 2 性能评估后决定）

### Data Architecture

**数据建模方式：SQLAlchemy 2.0 声明式映射 + Repository Pattern**
- 业务逻辑通过 Repository 层隔离数据访问
- Agent 子系统和业务 API 共享数据库，Repository 层统一数据访问入口
- 多模块（报价、储能、回测、审计）通过独立 Repository 保持领域边界

**时序数据分区：TimescaleDB 超表 + 连续聚合**
- 96时段数据使用 `create_hypertable` 自动按时间分区
- 连续聚合预计算日/月汇总视图，加速回测和报表查询
- 预估数据量：~2100万行/年（96时段 × 20电站 × 365天）

**数据校验策略：Pydantic 多层校验**
- Layer 1：API 入口 Pydantic schema 自动校验（类型、必填、格式）
- Layer 2：Service 层业务规则校验（96时段完整性、SOC范围、电价合理性）
- Layer 3：数据库 NOT NULL/CHECK 约束兜底

**缓存策略：混合模式**
- 外部数据源降级缓存：Cache-Aside（精确控制 TTL，满足 NFR18 30秒切换）
- 电站配置等热点读取：Read-Through（Redis 中间件自动管理）

**PostgreSQL 多 Schema 隔离：**
- `public`：业务数据（用户、电站、报价、储能、审计）
- `langgraph`：Agent 状态检查点
- `timeseries`：TimescaleDB 超表（历史电价、功率、结算数据）
- Phase 2 可按需拆分为独立实例

### Authentication & Security

**认证方式：JWT 双 Token**
- Access Token：短期（30分钟），携带用户 ID + 角色
- Refresh Token：长期（7天），httpOnly Cookie 存储
- 30分钟无操作自动登出（前端定时器 + Token 过期）
- Phase 2 可扩展 OAuth 2.0 接入企业 SSO/LDAP

**授权模式：RBAC + 资源级权限**
- 5种角色权限矩阵：Admin / Trader / StorageOperator / TradingManager / ExecutiveReadonly
- FastAPI Dependency 注入实现角色校验装饰器
- 数据行级过滤：用户-电站关联表 + SQLAlchemy Query Filter
- 交易员仅可访问自己负责的电站数据

**API 安全中间件栈：**
- CORS 白名单（仅允许前端域名）
- Rate Limiting（Redis 令牌桶，防暴力攻击）
- 请求体大小限制
- SQL 注入防护（ORM 参数化查询）
- CSRF Token（表单提交场景）

**Agent 安全防护：输入输出过滤层**
- 输入过滤：LangGraph 节点前清洗敏感信息和注入模式
- 输出校验：JSON Schema 校验格式合规性 + 内容安全检查
- Agent 输入主要来自系统数据，用户直接 Prompt 输入有限

**数据加密：传输加密 + 字段级存储加密**
- 传输层：Nginx TLS 1.2+ 终止
- 存储层：敏感字段（API Key、LLM 配置密钥）AES-256 加密
- 实现：Python `cryptography` 库 + SQLAlchemy TypeDecorator 封装加密字段类型
- 用户密码：bcrypt 哈希存储（不可逆）

### API & Communication Patterns

**API 设计：RESTful + OpenAPI**
- FastAPI 自动生成 OpenAPI/Swagger 文档
- URL 路径版本化：`/api/v1/`
- 资源命名规范：复数名词（`/api/v1/quotes`、`/api/v1/stations`）

**实时通信：SSE（Server-Sent Events）统一推送**
- Agent 协作进度、储能调度状态、数据新鲜度通知统一使用 SSE
- FastAPI `StreamingResponse` 实现，LangGraph 事件流天然适配
- SSE 内置自动断线重连（`EventSource` API）
- Nginx 反向代理无需额外 WebSocket upgrade 配置

**事件协议设计：**
```
event: agent_progress
data: {"run_id":"xxx","node":"prediction_agent","status":"completed","elapsed":3.2}

event: dispatch_status
data: {"command_id":"xxx","status":"confirmed","operator":"张三"}

event: data_freshness
data: {"source":"spot_price","last_updated":"2026-02-26T08:00:00","stale":false}
```

**错误处理：统一错误响应格式**
```json
{
    "code": "SOC_LIMIT_EXCEEDED",
    "message": "储能SOC超出安全范围",
    "detail": {"current_soc": 0.95, "max_soc": 0.9, "device_id": "ESS-001"},
    "trace_id": "abc-123-def"
}
```
- 业务错误码语义明确，`trace_id` 与 Langfuse 链路打通

### Frontend Architecture

**Pinia Store 结构：按功能模块拆分 + 电站 ID 索引**
```typescript
// stores/quote.ts
export const useQuoteStore = defineStore('quote', () => {
  const activeStationId = ref<string>('')
  const stationQuotes = reactive(new Map<string, QuoteState>())
  const currentQuote = computed(() => stationQuotes.get(activeStationId.value))
})
```
- 功能模块独立 Store：quote / storage / agent / station / user
- 切换电站仅改变 `activeStationId`，各电站状态独立保持

**组件架构：Composition API 组合式**
- `composables` 封装数据获取 + 状态管理 + 业务逻辑
- 示例：`useQuotePanel(stationId)` / `useAgentProgress(runId)`
- Ant Design Vue 组件 Props 驱动，无需额外 Container 包装

**路由设计：模块化路由**
- 按功能模块拆分路由文件（`quote.routes.ts`、`storage.routes.ts`）
- 路由 `meta` 定义权限：`meta: { roles: ['trader', 'admin'] }`
- 路由守卫统一权限校验

**前端性能：路由级懒加载 + 按需导入**
- 路由懒加载：`() => import('./views/Quote.vue')`
- Ant Design Vue 按需导入：`unplugin-vue-components`
- Vite 7 原生代码分割

### Infrastructure & Deployment

**CI/CD：MVP 手动部署脚本**
- Shell 脚本：前端构建、数据库迁移、Docker Compose 部署
- Phase 2 引入 GitLab CI（私有化部署，满足数据主权）

**环境配置：.env 多环境文件 + python-decouple**
- `.env.development` / `.env.production` 分环境配置文件
- Docker Compose `env_file` 引用对应环境配置
- Python 应用层 `python-decouple` 分层读取：系统环境变量 > .env 文件 > 代码默认值
- LLM 切换仅需修改 `.env` 中 `LLM_BASE_URL` 和 `LLM_MODEL`

**日志与监控：structlog + Langfuse**
- Python `structlog` 输出 JSON 结构化日志，包含 `trace_id`
- Agent 可观测性：Langfuse 全链路追踪（100% 记录）
- Docker 容器日志 + JSON 日志文件满足 MVP 排障需求
- Phase 2 按需引入 Prometheus 指标采集

**数据备份：pg_dump + WAL 归档**
- 每小时 `pg_dump` 全量备份（满足 RPO ≤ 1h）
- PostgreSQL WAL 日志持续归档，支持 PITR 时间点恢复
- 恢复脚本化，满足 RTO ≤ 4h
- Phase 2 评估主从复制需求

**扩展路径：渐进式**
- MVP：Docker Compose 单机
- Phase 2：Docker Swarm 简单集群（3-5 节点）
- Phase 3：K8s 完整编排（多客户隔离）

### Key Architecture Decision Points

**K1 — 回测引擎：混合模式**
- 快速回测：复用审计日志中的历史 Agent 输出，纯数值计算回放，Celery 批处理
- 深度回测：对选定时段重跑完整 Agent 流程（含 LLM 调用），验证策略调整效果
- 快速回测满足 NFR3（1年<10分钟），深度回测按需执行

**K2 — 省份规则引擎：配置 + 插件化混合**
- 参数差异：JSON 配置文件（电价范围、偏差考核比例等）
- 逻辑差异：Python 插件模块（`rules/guangdong.py`），策略模式 + `@register_province` 装饰器注册
- MVP 先支持 1-2 个省份，插件化架构支撑后续省份扩展

**K3 — PostgreSQL：单实例多 Schema 隔离**
- 见 Data Architecture 章节
- Phase 2 架构评估项：3年数据增长模型验证

**K4 — PDF 报告：Playwright 服务端渲染**
- Playwright 无头浏览器渲染前端报告页面为 PDF
- 复用技术栈（Playwright 同时用于 E2E 测试）
- Celery 异步任务执行，不阻塞主流程

### Decision Impact Analysis

**Implementation Sequence:**
1. PostgreSQL 多 Schema + TimescaleDB 初始化（数据基础）
2. FastAPI 项目结构 + Repository Pattern + Pydantic 校验（后端骨架）
3. JWT 认证 + RBAC 权限（安全基础）
4. RESTful API + 统一错误处理 + SSE 推送（通信层）
5. Vue 前端 + Pinia Store 结构 + 路由体系（前端骨架）
6. LangGraph Agent 编排 + Langfuse 集成（Agent 核心）
7. 省份规则引擎插件化架构（业务扩展）
8. 回测引擎混合模式 + PDF 渲染（高价值功能）

**Cross-Component Dependencies:**
- JWT 认证 → 所有 API 端点 + SSE 连接鉴权
- Repository Pattern → Agent 子系统 + 业务 API 共享数据访问
- SSE 推送 → Agent 进度 + 储能调度 + 数据新鲜度（统一事件协议）
- Pinia 电站 ID 索引 → 报价/储能/Agent 状态三个 Store 联动
- structlog trace_id → Langfuse 链路追踪 + 错误响应 → 前端错误展示

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 5大类共25+个 AI Agent 可能产生不一致实现的潜在冲突点

### Naming Patterns

**数据库命名规范：**
- 表名：snake_case 复数（`power_stations`、`quote_records`、`audit_logs`）
- 列名：snake_case（`station_id`、`created_at`、`soc_upper_limit`）
- 外键：`{被引用表单数}_id`（`station_id`、`user_id`）
- 索引：`ix_{表名}_{列名}`（`ix_quote_records_trading_date`）
- 约束：`ck_{表名}_{描述}`（`ck_storage_plans_soc_range`）

**API 命名规范：**
- 端点：snake_case 复数（`/api/v1/power_stations`、`/api/v1/quote_records`）
- 路径参数：`{station_id}`
- 查询参数：snake_case（`?trading_date=2026-02-26&page_size=20`）
- JSON 字段：snake_case（前后端统一，避免 camelCase ↔ snake_case 转换层）

**Python 代码命名规范：**
- 模块/文件：snake_case（`quote_service.py`、`station_repository.py`）
- 类名：PascalCase（`QuoteRecord`、`PowerStation`）
- 函数/方法：snake_case（`generate_quote`、`get_station_by_id`）
- 常量：UPPER_SNAKE_CASE（`MAX_SOC_LIMIT`、`DEFAULT_PAGE_SIZE`）

**Vue 前端命名规范：**
- 组件文件：PascalCase.vue（`QuotePanel.vue`、`StationSelector.vue`）
- composable 文件：use + PascalCase.ts（`useQuotePanel.ts`、`useAgentProgress.ts`）
- Store 文件：小写功能名.ts（`stores/quote.ts`、`stores/station.ts`）
- 路由文件：功能名.routes.ts（`quote.routes.ts`）
- 工具函数文件：camelCase.ts（`dateFormat.ts`、`apiClient.ts`）
- 组件 Props/Emits：camelCase（`:stationId`、`@quoteSubmitted`）
- CSS：Ant Design Vue 自带样式系统

### Structure Patterns

**后端项目组织：按功能模块分层**

```
api-server/
├── app/
│   ├── core/              # 框架级基础设施
│   │   ├── config.py      # python-decouple 配置
│   │   ├── database.py    # SQLAlchemy 引擎/会话
│   │   ├── security.py    # JWT + RBAC
│   │   └── exceptions.py  # 统一异常定义
│   ├── models/            # SQLAlchemy 模型（按模块）
│   │   ├── station.py
│   │   ├── quote.py
│   │   └── storage.py
│   ├── schemas/           # Pydantic 请求/响应 schema
│   │   ├── station.py
│   │   └── quote.py
│   ├── repositories/      # 数据访问层
│   │   ├── base.py        # BaseRepository 抽象
│   │   ├── station.py
│   │   └── quote.py
│   ├── services/          # 业务逻辑层
│   │   ├── quote_service.py
│   │   └── storage_service.py
│   ├── api/               # 路由端点
│   │   └── v1/
│   │       ├── stations.py
│   │       └── quotes.py
│   ├── events/            # SSE 事件推送
│   └── tasks/             # Celery 异步任务
├── rules/                 # 省份规则引擎插件
│   ├── base.py
│   └── guangdong.py
├── tests/                 # 测试（镜像 app/ 结构）
│   ├── unit/
│   └── integration/
├── alembic/               # 数据库迁移
└── .env.development
```

**前端项目组织：按功能模块**

```
web-frontend/
├── src/
│   ├── api/               # API 请求封装（按模块）
│   │   ├── client.ts      # Axios 实例 + 拦截器
│   │   ├── quote.ts
│   │   └── station.ts
│   ├── composables/       # 组合式函数
│   │   ├── useQuotePanel.ts
│   │   └── useAgentProgress.ts
│   ├── components/        # 可复用组件（按功能分目录）
│   │   ├── quote/
│   │   ├── storage/
│   │   └── common/
│   ├── views/             # 路由页面
│   │   ├── quote/
│   │   └── storage/
│   ├── stores/            # Pinia Store
│   │   ├── quote.ts
│   │   └── station.ts
│   ├── router/            # 模块化路由
│   │   ├── index.ts
│   │   └── modules/
│   ├── types/             # TypeScript 类型定义
│   └── utils/             # 工具函数
├── tests/
│   ├── unit/
│   └── e2e/
```

**测试位置：** 独立 `tests/` 目录，镜像源码结构（非 co-located），便于 CI 单独跑测试目录

### Format Patterns

**API 响应格式：**

```python
# 成功响应 — 直接返回数据（FastAPI 默认，Pydantic 自动序列化）
# GET /api/v1/stations/1
{
    "id": 1,
    "name": "广东某电站",
    "province": "guangdong",
    "created_at": "2026-02-26T08:00:00+08:00"
}

# 列表响应 — 统一分页结构
# GET /api/v1/stations?page=1&page_size=20
{
    "items": [...],
    "total": 42,
    "page": 1,
    "page_size": 20
}

# 错误响应 — 统一结构（见 API & Communication Patterns）
{
    "code": "STATION_NOT_FOUND",
    "message": "电站不存在",
    "detail": {"station_id": 999},
    "trace_id": "abc-123"
}
```

**日期时间格式：**
- API 传输：ISO 8601 带时区（`2026-02-26T08:00:00+08:00`）
- 数据库存储：UTC timestamp with time zone
- 前端展示：转换为北京时间（UTC+8），格式 `YYYY-MM-DD HH:mm`

**JSON 字段风格：**
- 前后端统一 snake_case（避免 camelCase ↔ snake_case 转换层）
- 布尔值：`true/false`
- 空值：使用 `null`，不省略字段
- 96 时段数据：数组 `[{period: 1, price: 0.35}, ...]`，`period` 范围 1-96

### Communication Patterns

**SSE 事件命名：小写 + 下划线**

```
event: agent_progress      # Agent 执行进度
event: dispatch_status      # 储能调度状态
event: data_freshness       # 数据新鲜度更新
event: quote_updated        # 报价数据更新
event: system_notification  # 系统级通知
```

**Pinia 状态更新规则：**
- Store 中只暴露 `ref`/`reactive` + `computed` + action 函数
- Action 命名：动词开头（`fetchQuotes`、`updatePeriod`、`resetState`）
- 异步 Action 内部处理 loading/error 状态，不依赖外部 try-catch
- Store 间通信通过 composable 层协调，不直接 Store 互调

### Process Patterns

**错误处理分层：**

```
前端 API 层（Axios 拦截器）
  → 401: 自动跳转登录
  → 403: 显示权限不足提示
  → 500: 显示通用错误 + trace_id
  → 业务错误码: 传递给组件层处理

后端 Service 层
  → 业务异常: raise BusinessError(code, message, detail)
  → 数据校验: Pydantic ValidationError（自动 422）
  → 系统异常: 全局 ExceptionHandler 捕获，记录 structlog，返回 500

Agent 层
  → Agent 执行异常: LangGraph 错误回调 → 降级规则引擎
  → LLM 调用超时: 重试1次 → 降级备选模型 → 降级规则引擎
  → Token 超限: 截断输入 → 记录告警
```

**Loading 状态约定：**
- 每个 Store action 管理自己的 `loading` 状态
- 命名：`isLoading` + 功能描述（`isLoadingQuotes`、`isGenerating`）
- 骨架屏用于首次加载，Spin 用于刷新/操作中
- 30 秒以上的长操作（Agent 生成报价）使用进度条 + SSE 实时更新

**重试策略：**
- LLM 调用：最多重试 1 次，间隔 2 秒
- 外部数据源 API：最多重试 2 次，指数退避（1s → 2s）
- 数据库操作：不重试，直接报错
- 前端 API 调用：网络错误重试 1 次，业务错误不重试

### Enforcement Guidelines

**所有 AI Agent 必须遵守：**
1. 数据库表名 snake_case 复数，列名 snake_case
2. API 端点 `/api/v1/` 前缀，snake_case 复数资源名
3. Python 代码遵循 PEP 8，Vue 代码遵循 Vue 官方风格指南
4. 所有 API 错误返回统一 `{code, message, detail, trace_id}` 结构
5. 日期时间 ISO 8601 带时区，数据库 UTC 存储
6. 测试放在独立 `tests/` 目录，镜像源码结构
7. 业务逻辑在 Service 层，数据访问在 Repository 层，不在 API 路由层写业务逻辑
8. 前端状态管理通过 Pinia Store + composables，不在组件内直接调 API

**反模式示例：**

| 反模式 | 正确做法 |
|--------|---------|
| `class users`（表名小写单数） | `class User`（模型 PascalCase），表名 `users`（snake_case 复数） |
| `/api/v1/getQuote`（动词端点） | `/api/v1/quotes/{id}`（RESTful 资源） |
| 在路由函数里写 SQL 查询 | 通过 Repository 层访问数据 |
| `userId`（API JSON camelCase） | `user_id`（统一 snake_case） |
| 组件内直接 `axios.get(...)` | 通过 `api/quote.ts` 封装 + composable 调用 |
| `loading = true` 散落在各处 | Store action 内统一管理 `isLoadingQuotes` |

## Project Structure & Boundaries

### Complete Project Directory Structure

```
ElectricityTradingPlatform/
├── docker-compose.yml              # MVP 单机部署编排
├── docker-compose.dev.yml          # 开发环境覆盖配置
├── .env.example                    # 环境变量模板
├── .env.development                # 开发环境配置
├── .env.production                 # 生产环境配置
├── .gitignore
├── README.md
│
├── web-frontend/                   # ===== Vue 3 前端 =====
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── nginx.conf                  # Nginx 反向代理配置
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.ts                 # 应用入口
│   │   ├── App.vue
│   │   ├── api/                    # API 请求封装
│   │   │   ├── client.ts           # Axios 实例 + 拦截器 + 错误处理
│   │   │   ├── auth.ts             # 登录/登出/刷新Token
│   │   │   ├── station.ts          # 电站 CRUD
│   │   │   ├── quote.ts            # 报价相关
│   │   │   ├── storage.ts          # 储能调度
│   │   │   ├── backtest.ts         # 回测
│   │   │   ├── data-import.ts      # 数据导入
│   │   │   ├── agent.ts            # Agent 状态/SSE
│   │   │   ├── audit.ts            # 审计日志
│   │   │   └── user.ts             # 用户管理
│   │   ├── composables/            # 组合式函数
│   │   │   ├── useAuth.ts          # 认证状态 + 权限校验
│   │   │   ├── useQuotePanel.ts    # 报价面板逻辑
│   │   │   ├── useStoragePlan.ts   # 储能计划逻辑
│   │   │   ├── useAgentProgress.ts # Agent SSE 进度监听
│   │   │   ├── useBacktest.ts      # 回测操作逻辑
│   │   │   ├── useDataImport.ts    # 数据导入向导逻辑
│   │   │   ├── useSSE.ts           # SSE 连接管理（通用）
│   │   │   └── usePagination.ts    # 分页逻辑（通用）
│   │   ├── components/             # 可复用组件
│   │   │   ├── common/             # 通用组件
│   │   │   │   ├── DataFreshnessBadge.vue
│   │   │   │   ├── StationSelector.vue
│   │   │   │   └── PageHeader.vue
│   │   │   ├── quote/              # 报价模块组件
│   │   │   │   ├── QuotePeriodTable.vue
│   │   │   │   ├── QuotePriceChart.vue
│   │   │   │   └── QuoteConfirmDialog.vue
│   │   │   ├── storage/            # 储能模块组件
│   │   │   │   ├── ChargePlanTimeline.vue
│   │   │   │   ├── SOCGauge.vue
│   │   │   │   └── DispatchCommandCard.vue
│   │   │   ├── agent/              # Agent 模块组件
│   │   │   │   ├── AgentProgressSteps.vue
│   │   │   │   └── DecisionChainPanel.vue
│   │   │   ├── backtest/           # 回测模块组件
│   │   │   │   ├── BacktestConfig.vue
│   │   │   │   ├── BacktestResultKPI.vue
│   │   │   │   └── RevenueWaterfall.vue
│   │   │   └── data/               # 数据管理组件
│   │   │       ├── ImportWizard.vue
│   │   │       └── DataQualityTable.vue
│   │   ├── views/                  # 路由页面
│   │   │   ├── auth/
│   │   │   │   └── LoginView.vue
│   │   │   ├── dashboard/
│   │   │   │   └── DashboardView.vue
│   │   │   ├── quote/
│   │   │   │   ├── QuoteDecisionView.vue
│   │   │   │   └── QuoteHistoryView.vue
│   │   │   ├── storage/
│   │   │   │   ├── StoragePlanView.vue
│   │   │   │   └── StorageMonitorView.vue
│   │   │   ├── backtest/
│   │   │   │   ├── BacktestCreateView.vue
│   │   │   │   └── BacktestResultView.vue
│   │   │   ├── data/
│   │   │   │   ├── StationConfigView.vue
│   │   │   │   └── DataImportView.vue
│   │   │   ├── audit/
│   │   │   │   └── AuditLogView.vue
│   │   │   └── admin/
│   │   │       └── UserManagementView.vue
│   │   ├── stores/                 # Pinia Store
│   │   │   ├── auth.ts
│   │   │   ├── station.ts
│   │   │   ├── quote.ts
│   │   │   ├── storage.ts
│   │   │   ├── agent.ts
│   │   │   └── backtest.ts
│   │   ├── router/                 # 模块化路由
│   │   │   ├── index.ts
│   │   │   └── modules/
│   │   │       ├── auth.routes.ts
│   │   │       ├── quote.routes.ts
│   │   │       ├── storage.routes.ts
│   │   │       ├── backtest.routes.ts
│   │   │       ├── data.routes.ts
│   │   │       ├── audit.routes.ts
│   │   │       └── admin.routes.ts
│   │   ├── types/                  # TypeScript 类型
│   │   │   ├── api.ts
│   │   │   ├── station.ts
│   │   │   ├── quote.ts
│   │   │   ├── storage.ts
│   │   │   └── agent.ts
│   │   └── utils/                  # 工具函数
│   │       ├── dateFormat.ts
│   │       ├── periodUtils.ts
│   │       └── permission.ts
│   └── tests/
│       ├── unit/
│       │   ├── composables/
│       │   ├── stores/
│       │   └── utils/
│       └── e2e/
│           ├── quote.spec.ts
│           └── auth.spec.ts
│
├── api-server/                     # ===== FastAPI 后端 =====
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── core/                   # 框架级基础设施
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # python-decouple 配置
│   │   │   ├── database.py         # SQLAlchemy 异步引擎/会话
│   │   │   ├── security.py         # JWT 生成/验证 + 密码哈希
│   │   │   ├── dependencies.py     # FastAPI 公共依赖
│   │   │   ├── exceptions.py       # BusinessError + 全局异常处理器
│   │   │   ├── encryption.py       # AES-256 字段加密 TypeDecorator
│   │   │   └── logging.py          # structlog 配置
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base 声明式基类 + 公共 Mixin
│   │   │   ├── user.py
│   │   │   ├── station.py
│   │   │   ├── quote.py
│   │   │   ├── storage.py
│   │   │   ├── backtest.py
│   │   │   ├── audit.py
│   │   │   └── data_import.py
│   │   ├── schemas/                # Pydantic Schema
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── auth.py
│   │   │   ├── station.py
│   │   │   ├── quote.py
│   │   │   ├── storage.py
│   │   │   ├── backtest.py
│   │   │   └── data_import.py
│   │   ├── repositories/           # 数据访问层
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # BaseRepository[T] 泛型基类
│   │   │   ├── user.py
│   │   │   ├── station.py
│   │   │   ├── quote.py
│   │   │   ├── storage.py
│   │   │   ├── backtest.py
│   │   │   └── audit.py
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── station_service.py
│   │   │   ├── quote_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── backtest_service.py
│   │   │   ├── data_import_service.py
│   │   │   └── audit_service.py
│   │   ├── api/                    # 路由端点
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # v1 总路由聚合
│   │   │       ├── auth.py
│   │   │       ├── stations.py
│   │   │       ├── quotes.py
│   │   │       ├── storage.py
│   │   │       ├── backtests.py
│   │   │       ├── data_imports.py
│   │   │       ├── audit_logs.py
│   │   │       ├── users.py
│   │   │       └── events.py       # SSE 推送端点
│   │   ├── events/                 # SSE 事件管理
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   └── schemas.py
│   │   └── tasks/                  # Celery 异步任务
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       ├── backtest_tasks.py
│   │       ├── pdf_tasks.py
│   │       └── import_tasks.py
│   ├── rules/                      # 省份规则引擎
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── guangdong.py
│   │   └── config/
│   │       └── guangdong.json
│   ├── alembic/                    # 数据库迁移
│   │   ├── env.py
│   │   ├── versions/
│   │   └── script.py.mako
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── services/
│       │   ├── repositories/
│       │   └── rules/
│       └── integration/
│           ├── api/
│           └── tasks/
│
├── agent-engine/                   # ===== LangGraph Agent 引擎 =====
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # LangGraph 应用入口
│   │   ├── config.py               # LLM 配置
│   │   ├── graphs/                 # LangGraph 图定义
│   │   │   ├── __init__.py
│   │   │   ├── coordinator.py      # 顶层 Supervisor 图
│   │   │   ├── prediction_subgraph.py
│   │   │   ├── strategy_subgraph.py
│   │   │   ├── storage_subgraph.py
│   │   │   └── risk_subgraph.py
│   │   ├── agents/                 # Agent 节点实现
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # BaseAgent 抽象
│   │   │   ├── coordinator_agent.py
│   │   │   ├── prediction_agent.py
│   │   │   ├── strategy_agent.py
│   │   │   ├── storage_agent.py
│   │   │   └── risk_control_agent.py
│   │   ├── tools/                  # Agent 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── market_data.py
│   │   │   ├── station_data.py
│   │   │   ├── rule_engine.py
│   │   │   └── calculation.py
│   │   ├── state/                  # LangGraph 状态定义
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── checkpoints/
│   │   │   └── postgres.py
│   │   ├── filters/                # 安全过滤层
│   │   │   ├── __init__.py
│   │   │   ├── input_filter.py
│   │   │   └── output_filter.py
│   │   └── observability/
│   │       ├── __init__.py
│   │       └── langfuse_setup.py
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── agents/
│       │   └── tools/
│       └── integration/
│           └── graphs/
│
├── scripts/                        # ===== 部署与运维脚本 =====
│   ├── deploy.sh
│   ├── backup.sh
│   ├── restore.sh
│   ├── migrate.sh
│   └── init-db.sh
│
└── docs/                           # ===== 项目文档 =====
    └── api-examples/
```

### Architectural Boundaries

**API 边界：**

| 边界 | 上游 | 下游 | 通信方式 |
|------|------|------|---------|
| 前端 → 后端 | web-frontend | api-server | REST API (`/api/v1/*`) |
| 前端 ← 后端 | api-server | web-frontend | SSE (`/api/v1/events/stream`) |
| 后端 → Agent | api-server | agent-engine | HTTP API（内部网络） |
| 后端 → Celery | api-server | celery-worker | Redis 消息队列 |
| Agent → 后端 | agent-engine | api-server | HTTP API（查询数据/写入结果） |
| Agent → LLM | agent-engine | ollama/vLLM | OpenAI 兼容 API |
| Agent → Langfuse | agent-engine | langfuse | HTTP API |

**数据边界：**

| Schema | 负责服务 | 读取服务 |
|--------|---------|---------|
| `public` | api-server | api-server、agent-engine（只读） |
| `langgraph` | agent-engine | agent-engine |
| `timeseries` | api-server（写入）、celery-worker（回测读取） | api-server、agent-engine |

**关键规则：** Agent Engine 对 `public` Schema 的访问是**只读**的。Agent 决策结果通过 HTTP API 回传 api-server，由 api-server 写入数据库。

### Requirements to Structure Mapping

| 功能模块 | FR 范围 | 前端 views/ | 后端 api/v1/ | 后端 services/ | Agent graphs/ |
|---------|---------|------------|-------------|---------------|--------------|
| 认证与用户管理 | FR1-FR4 | auth/, admin/ | auth.py, users.py | auth_service.py | — |
| 日前报价决策 | FR5-FR10, FR50-51 | quote/ | quotes.py | quote_service.py | coordinator.py（全图） |
| 历史回测 | FR11-FR16 | backtest/ | backtests.py | backtest_service.py | —（快速）/ 全图（深度） |
| 数据管理 | FR23-FR29 | data/ | data_imports.py, stations.py | data_import_service.py, station_service.py | — |
| 审计合规 | FR34-FR37 | audit/ | audit_logs.py | audit_service.py | — |
| 储能调度 | FR38-FR46 | storage/ | storage.py | storage_service.py | storage_subgraph.py |
| 多 Agent 协作 | FR54-FR58 | agent/ 组件 | events.py | — | graphs/* + agents/* |
| 省份规则 | 领域需求 | — | — | —（rules/ 独立模块） | tools/rule_engine.py |

**Cross-Cutting 映射：**

| 关注点 | 相关文件位置 |
|--------|------------|
| 审计日志 | `models/audit.py` + `services/audit_service.py` + 各 Service 审计调用 |
| 降级策略 | `agent-engine/agents/base.py` + `api-server/services/`（数据源降级） |
| 安全过滤 | `agent-engine/filters/` |
| SSE 推送 | `api-server/events/manager.py` + `web-frontend/composables/useSSE.ts` |
| 数据新鲜度 | `api-server/tasks/` + `events/` + `web-frontend/components/common/DataFreshnessBadge.vue` |

### Data Flow

```
用户操作（前端）
    ↓ REST API
api-server（校验 + 权限 + 业务逻辑）
    ↓ HTTP 内部调用
agent-engine（LangGraph 编排 → LLM 推理）
    ↓ SSE 事件
api-server → 前端（实时进度推送）
    ↓ HTTP 回调
api-server（Agent 结果写入数据库 + 审计记录）
    ↓ SSE 事件
前端（展示 AI 建议 → 交易员审核/微调/确认）
    ↓ REST API
api-server（最终决策写入 + 审计记录）
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** 所有技术选型版本兼容，无冲突。Vue 3.5 + Vite 7 + Pinia 3 前端栈互兼容；FastAPI + SQLAlchemy 2.0 + Pydantic 2 后端栈原生集成；LangGraph 1.0 + LangChain 1.2 Agent 栈版本对齐。

**Pattern Consistency:** snake_case 命名从数据库到 API JSON 到查询参数全链路统一；三层架构（API→Service→Repository）在项目结构中完整体现；SSE 事件协议在后端 `events/` 和前端 `composables/useSSE.ts` 两端对应。

**Structure Alignment:** 三个独立服务目录与 Docker Compose 服务清单对应；多 Schema 隔离通过 Alembic 迁移管理；每个功能模块在前端和后端都有对应目录映射。

### Requirements Coverage ✅

**功能需求：** 58 条 FR 全部有对应架构支撑，7 个功能模块均映射到具体目录和服务。

| FR 范围 | 需求描述 | 架构支撑 | 状态 |
|---------|---------|---------|------|
| FR1-FR4 | 用户认证与管理 | JWT 双Token + RBAC + 5角色 | ✅ |
| FR5-FR10 | 日前报价决策 | LangGraph 全图 + SSE 进度 + 审核确认流 | ✅ |
| FR11-FR16 | 历史回测 | 混合模式（快速+深度）+ Celery + PDF渲染 | ✅ |
| FR17-FR22 | 仪表盘与可视化 | Vue 前端 + @ant-design/charts + SSE 数据新鲜度 | ✅ |
| FR23-FR29 | 数据管理与导入 | 导入向导 + Celery 批处理 + Pydantic 多层校验 | ✅ |
| FR30-FR33 | 系统配置 | .env + python-decouple + API 端点 | ✅ |
| FR34-FR37 | 审计合规 | 审计模型（追加写入）+ structlog + Langfuse | ✅ |
| FR38-FR46 | 储能调度 | 储能子图 + SOC 硬校验 + 调度确认闭环 | ✅ |
| FR47-FR49 | 告警通知 | SSE 推送 + 前端通知组件 | ✅ |
| FR50-FR51 | 负电价/储能联合 | Agent 策略子图 + 储能子图联动 | ✅ |
| FR54-FR58 | 多Agent协作 | LangGraph Supervisor + 5个子图 + 降级 + 全链路记录 | ✅ |

**非功能需求：** 33 条 NFR 中 32 条已有明确架构决策支撑。NFR33（Agent 输出质量评估管道）已在 Cross-Cutting Concerns 中识别，标记为 Post-MVP 补充项。

### Implementation Readiness ✅

- 18 个核心架构决策均有明确选项、版本号和理由
- 8 条 AI Agent 强制执行规则 + 6 条反模式示例
- 三个服务的完整目录树（含具体文件名）
- 需求→结构映射表覆盖所有功能模块

### Gap Analysis

| 优先级 | Gap | 处理方式 |
|--------|-----|---------|
| Important | NFR33 Agent 质量评估目录未定义 | Phase 2 在 agent-engine/app/evaluation/ 实现 |
| Important | 5角色×30端点权限矩阵未显式列出 | Epic 拆分时补充 |
| Nice-to-have | 数据库 ER 图未绘制 | Story 实现时补充 |

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] 项目上下文深度分析（58 FR + 33 NFR）
- [x] 规模与复杂度评估（企业级）
- [x] 技术约束识别（7 项硬性约束）
- [x] 跨切面关注点映射（11 项）

**✅ Architectural Decisions**
- [x] 关键决策文档化并带版本号（18 项）
- [x] 技术栈完整指定
- [x] 集成模式定义
- [x] 性能考量已处理

**✅ Implementation Patterns**
- [x] 命名规范建立（数据库/API/Python/Vue）
- [x] 结构模式定义
- [x] 通信模式规定
- [x] 流程模式文档化

**✅ Project Structure**
- [x] 完整目录结构定义
- [x] 组件边界建立
- [x] 集成点映射
- [x] 需求→结构映射完成

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. 技术栈全部经过版本验证，无兼容性风险
2. LLM 部署分阶段策略（Ollama→vLLM→商业API）降低技术锁定风险
3. Agent Engine 对业务数据只读访问，数据写入归 api-server 统一管理，边界清晰
4. 三层降级策略（Agent→规则引擎、储能→无储能、数据源→缓存）保障业务连续性
5. 省份规则引擎插件化架构为多省份扩展预留清晰路径

**Areas for Future Enhancement:**
1. Phase 2：CI/CD（GitLab CI）、监控栈（Prometheus）、PostgreSQL 分库评估
2. Phase 3：K8s 编排、多租户隔离
3. Agent 输出质量评估管道（NFR33）
4. 完整权限矩阵和数据库 ER 图

### Implementation Handoff

**AI Agent Guidelines:**
- 严格遵循本文档的所有架构决策
- 使用统一的实现模式和命名规范
- 尊重项目结构和组件边界
- 所有架构疑问以本文档为准

**First Implementation Priority:**
1. `docker-compose.yml` + 各服务 `Dockerfile` 搭建开发环境
2. PostgreSQL 三 Schema 初始化 + TimescaleDB 启用
3. FastAPI 骨架（core/ + 第一个 API 端点）
4. Vue 前端骨架（路由 + Store + 第一个页面）
