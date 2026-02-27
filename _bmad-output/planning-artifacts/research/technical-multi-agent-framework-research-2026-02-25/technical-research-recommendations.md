# Technical Research Recommendations

## 实现路线图

```
第1-2周 ─── 基础验证
  │  搭建LangGraph开发环境
  │  实现预测Agent + 策略Agent + 协调Agent原型
  │  使用模拟数据验证端到端流程
  │
第3-4周 ─── Agent扩展
  │  新增储能调度Agent + 风控Agent
  │  接入功率预测模型（自有ML模型）
  │  切换PostgresSaver持久化
  │
第5-6周 ─── 真实数据集成
  │  接入历史交易数据
  │  实现96时段报价生成完整流程
  │  Human-in-the-loop审核流程开发
  │
第7-8周 ─── 前端集成
  │  交易员工作台对接LangGraph API
  │  WebSocket实时状态推送
  │  报价审核/修改界面
  │
第9-10周 ── 回测系统
  │  历史回测Agent开发
  │  AI策略 vs 实际交易对比
  │  收益归因分析
  │
第11-12周 ── 产品化
  │  Langfuse监控部署
  │  安全加固 + 审计日志
  │  性能优化（<30秒目标）
  │  Docker Compose生产部署
```

## 技术栈推荐汇总

| 层次 | 技术选择 | 替代方案 |
|------|---------|---------|
| **Agent编排** | LangGraph v1.0+ | — |
| **LLM框架** | LangChain (MIT) | — |
| **LLM模型** | Qwen3 8B（本地）+ GPT-4o（API） | DeepSeek R1、Claude |
| **LLM部署** | Ollama / vLLM | — |
| **后端框架** | FastAPI (Python) | Django |
| **数据库** | PostgreSQL + TimescaleDB | — |
| **Agent检查点** | langgraph-checkpoint-postgres | Redis |
| **前端** | React / Vue | — |
| **容器化** | Docker Compose（MVP）→ K8s（生产） | — |
| **监控追踪** | Langfuse（自托管） | — |
| **ML模型管理** | MLflow | — |
| **CI/CD** | GitHub Actions / GitLab CI | — |

## 成功指标与KPI

| 指标 | 目标值 | 衡量方式 |
|------|--------|---------|
| 96时段报价生成时间 | < 30秒 | API响应时间监控 |
| Agent协作成功率 | > 95% | Langfuse追踪 |
| 报价建议采纳率 | > 60%（初期） | 交易员审核日志统计 |
| 回测收益提升 | > 10% | 历史回测对比报告 |
| LLM Token月度成本 | < ¥8,000 | Langfuse成本追踪 |
| 系统可用性 | > 99%（交易窗口内） | 基础设施监控 |
