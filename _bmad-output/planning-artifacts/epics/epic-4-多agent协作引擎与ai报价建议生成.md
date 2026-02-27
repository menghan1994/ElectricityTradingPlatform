# Epic 4: 多Agent协作引擎与AI报价建议生成

**目标：** 系统通过多Agent协作自动生成96时段报价建议，交易员可查看AI建议及推荐理由、Agent决策链路、实时协作进度；系统支持中断-恢复、失败降级、检查点持久化、可观测性看板。

**FRs覆盖：** FR5, FR6, FR9, FR54, FR55, FR56, FR58, FR59, FR60

**相关NFRs：** NFR1(<30秒), NFR16(60秒降级), NFR28(成功率≥95%), NFR29(Token上限20K), NFR30(100%链路记录), NFR31(LLM热切换), NFR32(Prompt注入防护)

---

## Story 4.1: LangGraph多Agent协作图搭建与协调Agent

As a 系统,
I want 基于LangGraph搭建层级式Supervisor架构（协调Agent管理预测Agent→策略Agent→储能Agent→风控Agent的协作流程）,
So that 系统能端到端生成96时段报价建议。

**Acceptance Criteria:**

**Given** LangGraph Agent引擎服务已启动
**When** api-server通过HTTP API触发报价建议生成请求（含电站ID、交易日期）
**Then** 协调Agent按顺序编排：预测Agent→策略Agent→储能Agent（配有储能的电站）→风控Agent，最终输出96时段报量报价建议

**Given** 完整Agent协作链路
**When** 所有Agent成功完成
**Then** 输出包含每时段的报量（kW）、报价（元/MWh）、策略建议和推荐理由（规则描述级可解释性）

**Given** Agent协作过程中
**When** 每个Agent节点完成执行
**Then** 发射SSE状态事件（agent_progress），包含Agent名称、状态、耗时

**Given** 96时段报价建议生成
**When** 从触发到全部时段结果呈现
**Then** 端到端延迟<30秒（P95，10并发）

**Given** LLM模型配置
**When** 管理员修改配置文件中的LLM_BASE_URL和LLM_MODEL
**Then** 不同Agent可使用不同模型，切换仅需修改配置不改代码，操作耗时≤10分钟

---

## Story 4.2: Agent输入输出安全过滤与状态持久化

As a 系统,
I want Agent输入输出经过安全过滤防止Prompt注入，且协作状态持久化到PostgreSQL检查点,
So that 系统安全可靠，Agent流程中断后可从最近检查点恢复。

**Acceptance Criteria:**

**Given** 外部数据或用户输入传入Agent
**When** 数据经过输入过滤层
**Then** Prompt注入攻击模式被拦截（拦截率≥99%，覆盖≥20种典型注入模式），安全过滤规则可配置更新

**Given** Agent生成输出结果
**When** 输出经过输出校验层
**Then** 对输出进行JSON Schema格式合规性校验和内容安全检查，不合规输出被拦截并触发重试

**Given** Agent协作流程执行中
**When** 每个Agent节点完成执行
**Then** 执行状态、输入输出快照和检查点时间戳持久化存储到PostgreSQL langgraph Schema

**Given** Agent协作流程在某Agent节点中断（系统异常或超时）
**When** 系统重启或手动恢复
**Then** 流程从最近检查点恢复执行，无需重新运行已完成的Agent

**Given** 单次多Agent协作
**When** 累计LLM Token消耗达到20,000上限
**Then** 系统自动截断上下文并记录告警日志

---

## Story 4.3: Agent协作失败降级与规则引擎

As a 交易员（李娜）,
I want Agent协作失败时系统自动降级为规则引擎生成基础报价建议,
So that 即使AI系统异常，我仍然能获得报价参考继续工作。

**Acceptance Criteria:**

**Given** Agent协作过程中发生异常（Agent异常/超时60秒/输出校验失败）
**When** 单次链路累计失败超过2次
**Then** 系统自动降级为规则引擎，基于电站历史报价均值和当日功率预测生成96时段基础报价建议

**Given** 系统处于降级模式
**When** 交易员查看报价建议页面
**Then** 界面以醒目信息横幅（非阻断弹窗）提示当前处于降级模式及降级原因

**Given** 降级事件发生
**When** 系统记录事件
**Then** 降级事件自动记录至审计日志（含降级触发原因、时间、影响电站）

**Given** Agent系统从异常恢复
**When** 系统检测到Agent服务恢复正常
**Then** 自动提示交易员可切换回AI建议模式

**Given** AI引擎发生异常
**When** 系统检测异常
**Then** 在60秒内完成检测并切换至降级模式，核心功能（数据查看、手动操作）仍可用

---

## Story 4.4: Human-in-the-Loop中断-恢复机制

As a 交易员（李娜）,
I want Agent协作完成后系统暂停等待我审核，我可以批准、修改或拒绝后恢复流程,
So that AI建议始终经过我的人工确认，我拥有最终决策权。

**Acceptance Criteria:**

**Given** 多Agent协作完成并生成96时段报价建议
**When** 协调Agent输出最终结果
**Then** 系统通过中断-恢复机制暂停流程，等待交易员审核

**Given** 交易员查看AI报价建议
**When** 交易员批准建议
**Then** 流程恢复继续执行后续操作（如更新申报状态）

**Given** 交易员查看AI报价建议
**When** 交易员修改部分时段后确认
**Then** 修改内容记录后流程恢复，使用修改后的报价方案继续执行

**Given** 交易员查看AI报价建议
**When** 交易员拒绝建议并选择"重新生成"
**Then** 系统重新触发Agent协作流程生成新的报价建议

---

## Story 4.5: AI报价建议展示与Agent决策链路可视化

As a 交易员（李娜）,
I want 查看每个时段的AI报价建议及推荐理由，并能展开查看Agent决策链路,
So that 我能理解AI为什么这样建议，建立对AI的信任。

**Acceptance Criteria:**

**Given** Agent协作完成并生成报价建议
**When** 交易员查看报价建议页面
**Then** 展示每个时段的AI报价建议（报量kW、报价元/MWh）及推荐理由（规则描述级可解释性）

**Given** 某时段被系统识别为负电价风险时段
**When** 展示该时段报价建议
**Then** 负电价预警醒目标识（红色背景+警告图标+"负"文字Tag），对配有储能的电站同时展示储能充电建议（含预计SOC变化和后续放电窗口推荐）

**Given** 交易员查看AI建议
**When** 交易员点击"展开Agent决策链路"
**Then** 渐进式展开每个Agent的输入摘要、输出结果、推理耗时及置信度评分（Progressive Disclosure），使用面向用户的自然语言摘要

**Given** Agent协作正在进行中
**When** 交易员查看报价建议页面
**Then** 实时展示Agent协作进度步骤条（预测Agent完成→策略Agent计算中→储能Agent待启动...），通过SSE推送更新

---

## Story 4.6: Agent可观测性看板

As a 系统管理员（老周）,
I want 查看多Agent协作的运行指标看板并配置告警规则,
So that 我能监控Agent系统的健康状况，及时发现和处理问题。

**Acceptance Criteria:**

**Given** 管理员已登录并进入Agent可观测性看板
**When** 查看运行指标
**Then** 展示：各Agent调用成功率、平均耗时、Token消耗趋势、协作链路失败率Top原因

**Given** 管理员需要配置告警
**When** 设置告警规则（如协作成功率低于阈值、Token消耗超预算）
**Then** 规则保存成功，触发时通过页面通知推送告警

**Given** Agent可观测性平台（Langfuse自托管）
**When** 记录Agent调用链路
**Then** 100%的Agent调用链路（输入/输出/耗时/Token消耗/模型标识）被记录

**Given** 追踪数据
**When** 查询历史数据
**Then** 追踪数据保留≥90天

---
