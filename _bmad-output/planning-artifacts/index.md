# ElectricityTradingPlatform — 规划文档索引

> 本索引为所有规划文档提供内容摘要，帮助 AI Agent 按需选择性加载文件。

---

## 顶层文件

- **[product-brief-ElectricityTradingPlatform-2026-02-24.md](./product-brief-ElectricityTradingPlatform-2026-02-24.md)** — 新能源电力AI交易优化平台产品简案
  - 执行摘要：中国电力现货市场背景、痛点、四大模块解决方案
  - 核心愿景：问题陈述、影响、现有方案不足、提议方案
  - 目标用户：4类画像（交易员李娜、部长赵磊、管理层王总、储能运维陈工）
  - 用户旅程：交易员一天使用流程
  - 成功指标：用户/商业/技术 KPI 表
  - MVP范围：5大核心模块、排除项、V2-V3未来规划

- **[ux-design-specification.md](./ux-design-specification.md)** — 电力交易平台UX设计规范文档
  - 设计机会：Agent决策链路可视化、回测数据叙事、交易工作台一屏决策、储能调度时间轴
  - 关键设计决策：储能调度与报价呈现方式、可解释AI核心竞争力
  - 定义性体验：回测数据叙事时刻、AI报价审核信任时刻
  - 平台策略：纯桌面Web应用、本地部署、1920×1080+适配
  - 无缝交互：交互设计零思考目标列表

- **[ux-design-directions.html](./ux-design-directions.html)** — 四个UX设计方向探索与对比指南（HTML格式）
  - 方向A：经典三栏工作台（左侧电站列表、中央报价网格、右侧Agent面板）
  - 方向B：中央聚焦式（图标导航、最大化网格、Agent抽屉）
  - 方向C：仪表盘式（卡片化、全局态势感知、Grafana风格）
  - 方向D：叙事式回测报告（纵向数据叙事、瀑布图归因）
  - 对比总结：优劣势、权衡取舍、组合建议

---

## prd/ — 产品需求文档（分片）

- **[index.md](./prd/index.md)** — PRD完整目录与导航索引

- **[executive-summary.md](./prd/executive-summary.md)** — 平台核心价值主张与端到端架构概览
  - 中石油新能源AI电力交易决策平台，"AI分析、人做决策"
  - 多智能体协作架构：功率预测→报价策略→储能调度→风控审计
  - 源储协同优化：负电价保护、峰谷套利
  - 试点验证：1家省级公司、≥10%收益提升目标

- **[project-classification.md](./prd/project-classification.md)** — 项目定位与复杂度分类
  - 类型：SaaS B2B（Web应用+AI引擎+数据看板）
  - 领域：能源电力交易优化
  - 复杂度：高（多省规则、实时决策、AI集成、储能约束、国资合规）

- **[success-criteria.md](./prd/success-criteria.md)** — 用户/商业/技术成功的完整指标体系
  - 交易员：报价效率提升80%、偏差考核下降
  - 管理层：回测证明收益≥10%、储能贡献可追溯
  - 商业里程碑：3月Demo→6月试点→12月商业化→18月规模化
  - 核心KPI：采纳率≥70%、储能套利≥15%、日活≥90%

- **[user-journeys.md](./prd/user-journeys.md)** — 六大核心用户旅程与页面信息架构
  - 旅程1-2：交易员李娜（成功路径 + AI建议冲突边缘场景）
  - 旅程3：赵磊管理决策（收益汇总、采纳率、储能贡献拆解）
  - 旅程4：王总采购决策（回测演示、380万增收、负电价专题）
  - 旅程5：老周系统配置（引导式、规则模板、2天上线）
  - 旅程6a/6b：储能调度（日前MVP + 实时偏差Phase 2）
  - 核心页面：交易工作台、储能调度、回测分析、收益看板、系统配置

- **[domain-specific-requirements.md](./prd/domain-specific-requirements.md)** — 电力领域合规、技术约束、风险缓解
  - 合规：136号文/394号文、省级市场规则、多省差异化架构
  - 储能合规：并网功率约束、GB/T 36276安全标准
  - 数据合规：不出境、加密存储传输、三级管控
  - 技术约束：本地/私有云部署（硬性）、LangGraph架构
  - 风险缓解：规则模块化、人工审核防AI偏差、Agent降级

- **[innovation-novel-patterns.md](./prd/innovation-novel-patterns.md)** — 五大核心创新点与竞争差异化
  - 创新1：预测-储能-交易一体化引擎
  - 创新2：信任度渐进式人机协作（L1→L2→L3）
  - 创新3：历史回测驱动获客
  - 创新4：多智能体协作决策（Supervisor+子图）
  - 创新5：源储协同智能（负电价避损、峰谷套利、偏差平滑）
  - 竞品对标：碧通能源、清鹏智能、国能日新

- **[saas-b2b-specific-requirements.md](./prd/saas-b2b-specific-requirements.md)** — SaaS B2B多租户、权限、定价、集成、合规
  - 租户模型：单租户隔离部署、电站级数据隔离
  - 权限矩阵：5角色RBAC（管理员/交易员/储能运维/主管/高管只读）
  - 定价：电站数×功能模块×省份阶梯计费
  - 集成：交易中心API、气象API、SCADA、储能EMS
  - 合规：数据安全法三级管控、AI决策审计≥3年

- **[product-scope-phased-development.md](./prd/product-scope-phased-development.md)** — MVP策略与三期分阶段路线图
  - MVP（3个月）：端到端"AI比人工多赚钱"演示、4人团队
  - MVP验证：AI收益≥10%、储能套利≥15%、多Agent成功率≥95%
  - Phase 2（6-9个月）：中长期合约、深度学习、多省、信任度L2、MCP
  - Phase 3（12-18个月+）：多市场联动、自动提交、行业SaaS、强化学习

- **[functional-requirements.md](./prd/functional-requirements.md)** — 9大功能模块58项详细需求
  - 功率预测管理（FR1-4）：曲线展示、模型切换、API接入
  - 日前报价决策（FR5-10/50-51）：多Agent生成、逐时段微调、负电价预警
  - 历史回测分析（FR11-16）：AI vs实际对比、时段归因、PDF导出
  - 收益看板分析（FR17-22/53）：电站汇总、偏差费用、储能对比
  - 数据管理导入（FR23-29）：电站参数、储能模板、市场规则、Excel/CSV
  - 用户权限管理（FR30-33/52）：RBAC、电站绑定、数据隔离
  - 储能调度管理（FR38-46）：96时段计划、约束校验、SOC展示
  - 多智能体协作（FR54-58）：决策链路可视化、中断恢复、降级
  - 审计合规（FR34-37）：Agent级审计、3年保存不可篡改

- **[non-functional-requirements.md](./prd/non-functional-requirements.md)** — 性能/安全/可扩展/可靠性/集成/多Agent质量属性
  - 性能：报价<30秒、预测<5秒、回测<10分钟、10并发
  - 安全：TLS 1.2+、AES-256、30分钟超时、数据境内
  - 可扩展：单实例20电站3客户→10客户Phase 2
  - 可靠性：交易日99.5%、断点续传、60秒降级
  - 多Agent：成功率≥95%、Token上限20000、模型热切换、Prompt注入防护

---

## prd-validation-report/ — PRD验证报告（分片）

- **[index.md](./prd-validation-report/index.md)** — 验证报告目录索引

- **[validation-executive-summary.md](./prd-validation-report/validation-executive-summary.md)** — PRD整体验证评级4.8/5优秀，11维度全PASS
  - 历史8项CRITICAL/WARNING全部修复完成
  - 核心优势：信息密度满分、叙事连贯、可追溯完整
  - 结论：PRD已完全就绪可进入下游工作流

- **[completeness-validation.md](./prd-validation-report/completeness-validation.md)** — 完整性验证通过，10章节100%完整，零TODO/Stub

- **[format-detection.md](./prd-validation-report/format-detection.md)** — 格式检测通过，6/6核心章节符合BMAD标准

- **[holistic-quality-assessment.md](./prd-validation-report/holistic-quality-assessment.md)** — 整体质量4.5/5，高管可读性5/5，BMAD原则7/7达标

- **[implementation-leakage-validation.md](./prd-validation-report/implementation-leakage-validation.md)** — 实现泄漏验证，6处轻度泄漏可接受（Agent角色、品牌名）

- **[information-density-validation.md](./prd-validation-report/information-density-validation.md)** — 信息密度满分，762行零冗余零反模式

- **[input-documents.md](./prd-validation-report/input-documents.md)** — 输入文档清单，6份来源文档（PRD+简报+3研究+技术调研）

- **[measurability-validation.md](./prd-validation-report/measurability-validation.md)** — 可测量性验证通过，89项需求指标完整，6处轻度问题

- **[multi-agent-integration-coherence-validation.md](./prd-validation-report/multi-agent-integration-coherence-validation.md)** — 多Agent一致性验证通过，15项技术调研发现全覆盖

- **[product-brief-coverage.md](./prd-validation-report/product-brief-coverage.md)** — 产品简报覆盖率97%，新增多智能体协作引擎

- **[project-type-compliance-validation.md](./prd-validation-report/project-type-compliance-validation.md)** — SaaS B2B合规验证通过（多租户/权限/定价/集成/合规5项）

- **[smart-requirements-validation.md](./prd-validation-report/smart-requirements-validation.md)** — SMART验证，58项FR平均4.62/5，6项低分需补细节

- **[traceability-validation.md](./prd-validation-report/traceability-validation.md)** — 可追溯性验证通过，零孤立FR/成功标准/旅程

- **[domain-compliance-validation.md](./prd-validation-report/domain-compliance-validation.md)** — 领域合规验证通过（电网/安全/环保/运维/多Agent 4类全覆盖）

---

## research/ — 研究文档

### research/market-electricity-trading-platform-research-2026-02-24/ — 电力交易平台市场研究

- **[index.md](./research/market-electricity-trading-platform-research-2026-02-24/index.md)** — 市场研究目录索引

- **[research-overview.md](./research/market-electricity-trading-platform-research-2026-02-24/research-overview.md)** — 研究范围与目标：竞品对标与章鱼能源深度分析方法论

- **[客户行为与市场细分.md](./research/market-electricity-trading-platform-research-2026-02-24/客户行为与市场细分.md)** — 市场规模、客户行为模式、三类细分画像
  - 2023年交易量56,679亿千瓦时，2030年占比70%目标
  - 三类客户：大型能源集团、中型新能源运营商、售电公司
  - 80万从业人员，2025年缺口3.5万人

- **[客户痛点与未满足需求.md](./research/market-electricity-trading-platform-research-2026-02-24/客户痛点与未满足需求.md)** — P0痛点、采纳障碍、满意度差距
  - 136号文全面入市、负电价、偏差考核、96时段报价复杂性
  - 最大未满足需求："预测-交易一体化"端到端优化平台缺失

- **[竞争格局分析.md](./research/market-electricity-trading-platform-research-2026-02-24/竞争格局分析.md)** — 章鱼能源深度分析、国内外竞品矩阵对标
  - 章鱼能源90亿美元估值、Kraken管理50GW+
  - 国内：国能日新、清能互联、清鹏智能、远景智能
  - 八维度竞争力矩阵

- **[战略综合与建议.md](./research/market-electricity-trading-platform-research-2026-02-24/战略综合与建议.md)** — 市场机遇评估、竞争策略、风险应对
  - 核心定位："中国新能源电力交易的AI大脑"
  - 差异化：预测-交易一体化 + AI原生 + 回测驱动销售
  - 1-2年竞争窗口，碧通能源本地化需时间

- **[调研结论.md](./research/market-electricity-trading-platform-research-2026-02-24/调研结论.md)** — 核心洞察总结与平台定位建议
  - 2025-2030年40%+复合增长，2030年43.66亿元SaaS市场
  - "AI建议+人工确认"最契合国资企业需求

---

### research/chinese-competitors-deep-dive-2026-02-24/ — 中国竞品深度分析（10家公司）

- **[index.md](./research/chinese-competitors-deep-dive-2026-02-24/index.md)** — 中国竞品研究总目录框架

- **[一国能日新-guoneng-rixin-上市龙头.md](./research/chinese-competitors-deep-dive-2026-02-24/一国能日新-guoneng-rixin-上市龙头.md)** — 功率预测市占第一的上市龙头
  - 预测收入2.05亿，续费率95%+，电交易平台覆盖5省
  - 优势：市占率第一、客户基数大；劣势：电交易占比低

- **[二清能互联-tsintergy-清华系运筹优化专家.md](./research/chinese-competitors-deep-dive-2026-02-24/二清能互联-tsintergy-清华系运筹优化专家.md)** — 清华电机系背景的运筹优化平台
  - 2025年获2亿融资，覆盖18省，火电交易市占前三

- **[三清鹏智能-清鹏能源-tsingroc-ai交易agent先锋.md](./research/chinese-competitors-deep-dive-2026-02-24/三清鹏智能-清鹏能源-tsingroc-ai交易agent先锋.md)** — 清华孵化的能源AI大模型与交易Agent
  - 三大模型融合（能源LLM/时序LLM/时空LLM），击败90%人类交易员

- **[四远光软件-ygsoft-电力财务软件龙头跨界.md](./research/chinese-competitors-deep-dive-2026-02-24/四远光软件-ygsoft-电力财务软件龙头跨界.md)** — 上市20年的电力财务龙头向智慧能源拓展
  - 营收20+亿，购售电云平台服务40+家售电公司

- **[五朗新科技朗新集团-longshine-能源数字化ai入市.md](./research/chinese-competitors-deep-dive-2026-02-24/五朗新科技朗新集团-longshine-能源数字化ai入市.md)** — 能源数字化+AI双驱动平台
  - 25省售电资质，80万座光伏电站数据，AI交易智能体研发中

- **[六鲸能云-jnengyun-光储数智化saas平台.md](./research/chinese-competitors-deep-dive-2026-02-24/六鲸能云-jnengyun-光储数智化saas平台.md)** — 光储融合运维与电力交易SaaS
  - 兼容20+品牌，标准版5天上线，客户含华润/国电投

- **[七中恒博瑞-电网信息化老兵.md](./research/chinese-competitors-deep-dive-2026-02-24/七中恒博瑞-电网信息化老兵.md)** — 中恒电气子公司，电网信息化20年向交易拓展

- **[八迈能科技-meinergy.md](./research/chinese-competitors-deep-dive-2026-02-24/八迈能科技-meinergy.md)** — 信息极度稀少的综合能源服务平台

- **[九电查查-泛能网-数据服务与综合能源平台.md](./research/chinese-competitors-deep-dive-2026-02-24/九电查查-泛能网-数据服务与综合能源平台.md)** — 电查查数据平台 + 泛能网新奥运营平台对比
  - 泛能网：9500企业、200园区、267专利、11项国标

- **[十补充竞争者其他值得关注的公司.md](./research/chinese-competitors-deep-dive-2026-02-24/十补充竞争者其他值得关注的公司.md)** — 心知能源（气象PaaS转型）+ 飔合科技（大模型交易服务）

- **[十一竞争格局总览.md](./research/chinese-competitors-deep-dive-2026-02-24/十一竞争格局总览.md)** — 五层市场分层与关键能力对比矩阵
  - 市场规模：2025年5.6亿→2030年43.66亿
  - 驱动力：136号文、394号文、3.5万交易人才缺口

- **[十二信息来源汇总.md](./research/chinese-competitors-deep-dive-2026-02-24/十二信息来源汇总.md)** — 十个企业和行业信息来源清单

---

### research/international-competitors-ai-energy-trading-2026-02-24/ — 国际竞品AI能源交易分析（7家公司）

- **[index.md](./research/international-competitors-ai-energy-trading-2026-02-24/index.md)** — 国际竞品调研目录索引

- **[一autogrid现为uplightschneider-electric体系.md](./research/international-competitors-ai-energy-trading-2026-02-24/一autogrid现为uplightschneider-electric体系.md)** — AutoGrid/Uplight/施耐德VPP平台
  - 管理6000MW VPP，算法成熟但需大幅本地化

- **[二stem-incathena-powertrack-optimizer平台.md](./research/international-competitors-ai-energy-trading-2026-02-24/二stem-incathena-powertrack-optimizer平台.md)** — Stem储能AI优化引擎（2025年升级为PowerTrack）
  - 管理2GWh储能/30GW太阳能，覆盖55国，全球储能优化领先

- **[三uplight.md](./research/international-competitors-ai-energy-trading-2026-02-24/三uplight.md)** — Uplight客户参与+DER管理，估值15亿美元
  - 97%预测准确率，80+家公用事业，1.1亿终端用户

- **[四远景智能-envision-digitalenos平台.md](./research/international-competitors-ai-energy-trading-2026-02-24/四远景智能-envision-digitalenos平台.md)** — 中国领先能源物联网AI平台（唯一本土国际竞品）
  - 估值265亿人民币，管理400GW资产，能源大模型

- **[五tesla-autobidder.md](./research/international-competitors-ai-energy-trading-2026-02-24/五tesla-autobidder.md)** — 特斯拉硬软一体化储能交易平台
  - 46.7GWh年部署，能源业务128亿美元；中国政治风险大

- **[六next-kraftwerkeshell旗下.md](./research/international-competitors-ai-energy-trading-2026-02-24/六next-kraftwerkeshell旗下.md)** — 欧洲最大VPP运营商（Shell旗下）
  - 10GW+ VPP，15000+资产，8欧洲国家；无亚太布局

- **[七energy-exemplarplexos平台.md](./research/international-competitors-ai-energy-trading-2026-02-24/七energy-exemplarplexos平台.md)** — 全球能源市场仿真软件标杆
  - PLEXOS唯一多能源系统统一仿真工具，450+客户68国

- **[八七家公司横向对比总结.md](./research/international-competitors-ai-energy-trading-2026-02-24/八七家公司横向对比总结.md)** — 七家国际竞品核心能力/规模/中国机会综合对标
  - 关键启示：远景智能是唯一具备中国市场深度的直接竞品

---

### research/technical-multi-agent-framework-research-2026-02-25/ — 多智能体框架技术研究

- **[index.md](./research/technical-multi-agent-framework-research-2026-02-25/index.md)** — 技术研究报告目录与工作流元数据

- **[research-overview.md](./research/technical-multi-agent-framework-research-2026-02-25/research-overview.md)** — 研究范围方法论与核心发现摘要
  - LangGraph v1.0+选型确定、层级式Supervisor+子图、12周MVP路线

- **[technical-research-scope-confirmation.md](./research/technical-multi-agent-framework-research-2026-02-25/technical-research-scope-confirmation.md)** — 研究范围目标确认（框架选型/架构/技术栈/集成/性能）

- **[technology-stack-analysis.md](./research/technical-multi-agent-framework-research-2026-02-25/technology-stack-analysis.md)** — 六大主流多智能体框架详细对标
  - LangGraph、CrewAI、AutoGen/AG2、MetaGPT、OpenAI Agents SDK、Claude Agent SDK
  - 性能基准对比、电力交易应用现状、MCP协议趋势
  - 最终选型：LangGraph（图结构编排、持久化检查点、最低延迟）

- **[integration-patterns-analysis.md](./research/technical-multi-agent-framework-research-2026-02-25/integration-patterns-analysis.md)** — LangGraph与外部系统集成模式
  - Supervisor层级架构、共享状态Reducer、Command路由
  - MCP协议标准化、MLflow模型管理、Human-in-the-Loop中断恢复
  - 完全自托管安全模式与数据合规

- **[architectural-patterns-and-design.md](./research/technical-multi-agent-framework-research-2026-02-25/architectural-patterns-and-design.md)** — 电力交易多Agent推荐架构设计
  - 层级式Supervisor+子图（金融任务+80.9%性能）
  - 并行执行策略、模型无关架构（Qwen3+商业API混合）
  - PostgreSQL持久化、Docker Compose→K8s部署、安全矩阵

- **[implementation-approaches-and-technology-adoption.md](./research/technical-multi-agent-framework-research-2026-02-25/implementation-approaches-and-technology-adoption.md)** — MVP分阶段落地策略与技术采纳
  - 12周三阶段路线图（基础验证→核心功能→产品化）
  - 测试策略、LLM成本估算（¥2,000-8,000/月）、六大成本优化
  - 5人最小团队、40%多Agent试点失败原因分析

- **[technical-research-recommendations.md](./research/technical-multi-agent-framework-research-2026-02-25/technical-research-recommendations.md)** — 实现路线图、技术栈推荐、成功KPI指标
  - 周粒度12周时间表、容器化部署演进、报价生成/Agent成功率/采纳率KPI

- **[研究综合与结论.md](./research/technical-multi-agent-framework-research-2026-02-25/研究综合与结论.md)** — 研究成果总结、战略建议、技术前瞻
  - AI能源市场2030年183.1亿美元
  - 5项战略建议：立即验证、端到端、混合LLM、并行、培训
  - 技术机会：MCP标准化→强化学习→数字孪生
