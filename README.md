# 电力交易智能决策平台 (ElectricityTradingPlatform)

新能源电力交易智能决策平台，集成AI多Agent协作引擎，为交易员提供日前报价建议、储能调度优化、收益归因分析等功能。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3.5 + TypeScript + Vite 7 + Ant Design Vue 4 |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Agent引擎 | LangGraph 1.0 + LangChain 1.2 |
| 数据库 | PostgreSQL 18 + TimescaleDB |
| 缓存/队列 | Redis 7 + Celery 5.6 |
| LLM推理 | Ollama (Qwen3 8B) |
| 可观测性 | Langfuse 3 (自托管) |

## 快速启动

### 前置条件

- Docker & Docker Compose
- Git

### 步骤

```bash
# 1. 克隆代码
git clone <repo-url>
cd ElectricityTradingPlatform

# 2. 复制环境配置
cp .env.example .env

# 3. 启动所有服务（开发模式）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# 4. 访问服务
# 前端: http://localhost:5173 (开发模式) 或 http://localhost:80 (生产模式)
# API:  http://localhost:8000/api/v1/health
# Langfuse: http://localhost:3000
```

### 生产模式启动

```bash
docker compose up --build -d
```

## 项目结构

```
ElectricityTradingPlatform/
├── web-frontend/      # Vue 3 前端
├── api-server/        # FastAPI 后端
├── agent-engine/      # LangGraph Agent引擎
├── scripts/           # 运维脚本
├── docker-compose.yml # 生产环境编排
└── docker-compose.dev.yml # 开发环境覆盖
```

## 数据库

PostgreSQL 三Schema隔离：

| Schema | 用途 | 主写入者 |
|--------|------|---------|
| `public` | 业务数据 | api-server |
| `langgraph` | Agent状态检查点 | agent-engine |
| `timeseries` | TimescaleDB时序数据 | api-server |

## 运维脚本

```bash
scripts/deploy.sh    # 部署
scripts/backup.sh    # 数据库备份
scripts/restore.sh   # 数据库恢复
scripts/migrate.sh   # Alembic迁移
scripts/init-db.sh   # 数据库初始化（Docker自动执行）
```
