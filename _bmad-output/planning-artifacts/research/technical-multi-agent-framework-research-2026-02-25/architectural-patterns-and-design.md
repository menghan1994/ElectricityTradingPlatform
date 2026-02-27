# Architectural Patterns and Design

## 系统架构模式 — LangGraph电力交易多Agent系统

### 推荐架构：层级式Supervisor + 专业子图

基于对180种Agent配置的量化评估研究，以及LangGraph在电力交易场景中的适配性分析，推荐以下架构：

```
┌─────────────────────────────────────────────────────┐
│                  Web Frontend                        │
│            （交易员工作台 / 管理看板）                  │
├─────────────────────────────────────────────────────┤
│                  API Gateway                         │
│          （REST API / WebSocket实时推送）              │
├─────────────────────────────────────────────────────┤
│              LangGraph Orchestration Layer            │
│  ┌─────────────────────────────────────────────┐    │
│  │         协调Agent（Root Supervisor）          │    │
│  │    ┌─────────┬──────────┬──────────┐        │    │
│  │    │预测子图  │策略子图   │储能子图   │        │    │
│  │    │Subgraph │Subgraph  │Subgraph  │        │    │
│  │    │         │          │          │        │    │
│  │    │风电预测  │报价引擎   │调度优化   │        │    │
│  │    │光伏预测  │市场规则   │SOC管理   │        │    │
│  │    │电价预测  │风控审计   │          │        │    │
│  │    └─────────┴──────────┴──────────┘        │    │
│  │              ↕ Human-in-the-Loop              │    │
│  │         [交易员审核中断点]                      │    │
│  └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│                  Service Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │ML Model  │ │External  │ │Data Processing   │    │
│  │Service   │ │API Proxy │ │Service           │    │
│  │(预测模型) │ │(交易中心) │ │(数据清洗/ETL)    │    │
│  └──────────┘ └──────────┘ └──────────────────┘    │
├─────────────────────────────────────────────────────┤
│                  Data Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │PostgreSQL│ │Time-     │ │File Storage      │    │
│  │(业务数据 │ │Series DB │ │(导入文件/报告)    │    │
│  │+检查点)  │ │(历史数据) │ │                  │    │
│  └──────────┘ └──────────┘ └──────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**架构选择理由：**
- 层级式（Centralized）架构在金融/交易类任务中性能提升最高（+80.9%），优于去中心化（+74.5%）和混合式（+73.2%）
- 电力交易的96时段报价生成是高度协作的顺序+并行混合任务，适合Supervisor协调
- 子图（Subgraph）隔离各领域Agent的状态和上下文，降低复杂度

_Sources: [Google Agent系统扩展研究](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/), [多Agent架构设计](https://www.oreilly.com/radar/designing-effective-multi-agent-architectures/), [企业Agent架构模式](https://nexaitech.com/multi-ai-agent-architecutre-patterns-for-scale/)_

### 并行执行策略

LangGraph支持两种核心并行模式，均适用于电力交易场景：

1. **Scatter-Gather（分散-聚合）**：
   - 预测Agent并行执行风电、光伏、电价预测
   - 协调Agent聚合所有预测结果后传递给策略Agent
   - 适合MVP中的预测子图

2. **Pipeline并行**：
   - 不同电站的报价策略可流水线式并行生成
   - 适合多电站场景的扩展

**扩展性关键原则：**
- 多Agent系统天然支持水平扩展——增加Agent或复制角色即可
- 但对于顺序工作流（如96时段逐一分析），增加Agent可能产生递减收益甚至性能下降
- 应将并行化聚焦在**电站间**（多电站并行）而非**时段内**（96时段顺序）

_Sources: [Agent扩展科学](https://arxiv.org/abs/2512.08296), [多Agent高吞吐架构](https://medium.com/@adarshshrivastav/multi-agent-systems-architectural-patterns-for-high-throughput-processing-f971c451d698)_

## 设计原则与最佳实践

### LangGraph生产级设计原则

1. **Agent单一职责**：每个Agent聚焦一个明确的领域——计划、研究、验证、执行分离
2. **条件路由**：基于Agent置信度评分或外部系统状态进行动态路由
3. **检查点持久化**：
   - 生产环境必须使用 `PostgresSaver`（而非`MemorySaver`，后者仅供开发）
   - 每个Channel值单独存储并版本化，新检查点仅存储变更的值
   - 需设置 `autocommit=True` 和 `row_factory=dict_row`
4. **幂等性设计**：Agent操作应设计为幂等的，支持安全重试
5. **可观测性**：使用Langfuse（自托管）替代LangSmith实现生产监控

_Sources: [LangGraph生产最佳实践](https://medium.com/@kacperwlodarczyk/advanced-multi-agent-development-with-langgraph-expert-guide-best-practices-2025-4067b9cec634), [PostgreSQL检查点配置](https://pypi.org/project/langgraph-checkpoint-postgres/), [LangGraph持久化指南](https://fast.io/resources/langgraph-persistence/)_

### 模型无关架构（Model-Agnostic）

LangChain的模型抽象层使LangGraph天然支持模型无关设计：

- **本地开源模型**：通过Ollama或vLLM部署Qwen3（8B）、DeepSeek R1等国产模型
- **商业API**：通过LangChain接口接入GPT-4o、Claude等（需评估数据合规）
- **混合方案**：不同Agent可使用不同模型——高推理Agent用强模型，简单分类Agent用轻量模型
- **模型切换零成本**：只需更改ChatOllama/ChatOpenAI配置，Agent代码无需修改

**MVP推荐的LLM方案：**
```python
# 方案A：完全本地化（满足最严格的数据合规）
from langchain_ollama import ChatOllama
llm = ChatOllama(model="qwen3:8b-q4_K_M", temperature=0)

# 方案B：商业API（性能更优，需评估数据边界）
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 方案C：混合（推荐）—— 核心推理用商业API，数据处理用本地模型
```

**注意：** DeepSeek R1的小参数版本（7B/1.5B）在生成JSON格式输出时存在困难，需要Fallback机制。Qwen3 8B在Agent场景中表现更稳定。

_Sources: [Qwen3 LangGraph集成](https://dev.to/composiodev/a-comprehensive-guide-to-building-a-deep-research-agent-with-qwen3-locally-1jgm), [LangGraph本地深度研究](https://github.com/langchain-ai/local-deep-researcher), [LangChain模型无关指南](https://towardsai.net/p/machine-learning/llm-ai-agent-applications-with-langchain-and-langgraph-part-29-model-agnostic-pattern-and-llm-api-gateway)_

## 数据架构模式

### 状态持久化 — PostgreSQL

- **LangGraph检查点**：使用 `langgraph-checkpoint-postgres` 包，将Agent状态持久化到PostgreSQL
- **增量存储**：只存储状态变更，减少I/O开销
- **线程隔离**：每次报价流程使用唯一 `thread_id`，支持多电站并行不干扰
- **暂停-恢复**：进程重启后从最后检查点无缝恢复

### 时序数据

- 96时段功率/电价预测数据、历史交易数据适合时序数据库存储
- MVP可先用PostgreSQL + TimescaleDB扩展，降低运维复杂度

### 数据流架构

```
外部数据源 → Data Processing Service → PostgreSQL/TimescaleDB
                                            ↓
LangGraph Agent Graph ← 通过Tool读取 ← Service Layer
       ↓
  状态检查点 → PostgreSQL (checkpoints表)
       ↓
  最终结果 → API → Frontend
```

_Sources: [LangGraph PostgreSQL持久化](https://ai.plainenglish.io/using-postgresql-with-langgraph-for-state-management-and-vector-storage-df4ca9d9b89e), [检查点最佳实践](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025), [Postgres Checkpointer内部](https://blog.lordpatil.com/posts/langgraph-postgres-checkpointer/)_

## 部署与运维架构

### MVP部署方案

```
Docker Compose（单机部署）
├── langgraph-app          # LangGraph Agent应用
├── web-frontend           # 交易员工作台
├── api-server             # REST API服务
├── postgresql             # 业务数据 + LangGraph检查点
├── ollama (可选)          # 本地LLM服务
├── langfuse               # 观测与追踪
└── redis (可选)           # 缓存/消息队列
```

### 生产级扩展方案

```
Kubernetes集群
├── LangGraph App (Deployment, 水平扩展)
├── API Gateway (Ingress)
├── PostgreSQL (StatefulSet + PV)
├── Langfuse (Deployment)
├── vLLM/Ollama (GPU节点, 服务本地模型)
└── Monitoring (Prometheus + Grafana)
```

**关键决策：**
- MVP使用Docker Compose简化部署，验证后迁移至K8s
- PostgreSQL同时承担业务数据和LangGraph检查点存储
- Langfuse替代LangSmith实现完全自托管的Agent可观测性

## 安全架构模式

针对国资企业的安全要求：

| 安全层 | 措施 | 实现方式 |
|--------|------|---------|
| 数据合规 | 100%本地化，无数据出境 | Docker/K8s私有部署 |
| LLM安全 | 本地部署开源模型 | Ollama/vLLM + Qwen/DeepSeek |
| 传输安全 | TLS 1.2+ | Nginx反向代理 + 证书 |
| 访问控制 | RBAC + 会话管理 | JWT + 30分钟超时 |
| 审计追溯 | Agent决策全链路记录 | LangGraph检查点 + Langfuse追踪 |
| 数据加密 | 敏感数据加密存储 | PostgreSQL + AES-256 |

_Sources: [Agentic AI能源行业应用](https://www.xenonstack.com/blog/agentic-ai-energy-sector), [多Agent企业架构](https://arxiv.org/html/2601.13671v1), [LangGraph分布式Agent](https://icdcs2025.icdcs.org/tutorial-distributed-multi-agent-ai-systems-scalability-challenges-and-applications/)_
