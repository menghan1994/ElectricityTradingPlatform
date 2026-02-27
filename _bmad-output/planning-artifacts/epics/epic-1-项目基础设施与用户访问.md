# Epic 1: 项目基础设施与用户访问

**目标：** 系统管理员可以登录、管理用户和角色、配置绑定关系；所有用户安全登录并按权限访问数据。

**FRs覆盖：** FR30, FR31, FR32, FR33, FR52

**相关NFRs：** NFR6(TLS), NFR7(AES-256), NFR8(密码策略/会话超时/锁定), NFR9(数据不出境)

**架构需求：** Docker Compose编排、三Schema数据库初始化、JWT双Token、RBAC 5角色、FastAPI骨架、Vue前端骨架

---

## Story 1.1: 项目脚手架与开发环境搭建

As a 开发团队成员,
I want 一个完整的项目脚手架（前端Vue 3 + 后端FastAPI + Agent Engine + Docker Compose编排 + PostgreSQL三Schema初始化）,
So that 团队可以在统一的开发环境中开始编码。

**Acceptance Criteria:**

**Given** 开发者克隆代码仓库
**When** 执行 `docker-compose up`
**Then** 以下服务全部启动并通过健康检查：web-frontend(Nginx)、api-server(FastAPI)、postgresql(含public/langgraph/timeseries三个Schema + TimescaleDB扩展)、redis、langfuse
**And** FastAPI `/api/v1/health` 返回200
**And** Vue前端可通过浏览器访问并显示初始页面
**And** PostgreSQL timeseries Schema中TimescaleDB扩展已启用
**And** 项目目录结构符合架构文档定义（web-frontend/、api-server/、agent-engine/、scripts/）
**And** `.env.example` 包含所有必需环境变量模板

---

## Story 1.2: 用户认证（登录/登出/会话管理）

As a 系统用户,
I want 通过用户名和密码安全登录系统，并在无操作30分钟后自动登出,
So that 我的账户和数据安全受到保护。

**Acceptance Criteria:**

**Given** 数据库中存在已创建的用户账户
**When** 用户输入正确的用户名和密码并提交登录
**Then** 系统返回Access Token（30分钟有效期）和Refresh Token（7天，httpOnly Cookie存储）
**And** 用户被重定向到首页

**Given** 用户已登录
**When** 30分钟内无任何操作
**Then** 会话自动过期，用户被重定向到登录页

**Given** 用户连续5次输入错误密码
**When** 第5次登录失败
**Then** 账户被锁定15分钟，期间无法登录，并提示锁定剩余时间

**Given** 用户已登录
**When** 用户点击登出
**Then** Access Token失效、Refresh Token Cookie被清除、用户被重定向到登录页

**Given** 用户输入的密码不满足强密码策略（<8位或缺少大小写/数字/特殊字符）
**When** 注册或修改密码时
**Then** 系统拒绝并提示具体的密码要求

---

## Story 1.3: 用户账户管理与角色分配

As a 系统管理员（老周）,
I want 创建用户账户、编辑用户信息、重置密码、停用/启用账户，并为用户分配角色,
So that 交易团队的每个成员都有正确的系统访问权限。

**Acceptance Criteria:**

**Given** 管理员已登录
**When** 管理员在用户管理页面填写新用户信息（用户名、姓名、联系方式）并提交
**Then** 新用户账户创建成功，分配默认初始密码，操作记录写入审计日志

**Given** 管理员查看用户列表
**When** 管理员选择一个用户并修改其信息
**Then** 用户信息更新成功，变更前后值记录写入审计日志

**Given** 管理员选择一个用户
**When** 管理员执行"重置密码"操作
**Then** 用户密码被重置为系统生成的临时密码，操作记录写入审计日志

**Given** 管理员选择一个活跃用户
**When** 管理员执行"停用账户"操作
**Then** 用户状态变为"已停用"，该用户无法登录，操作记录写入审计日志

**Given** 管理员选择一个用户
**When** 管理员为其分配角色（管理员/交易员/储能运维员/交易主管/高管只读）
**Then** 角色分配成功，用户下次登录后获得对应权限，角色变更记录写入审计日志

---

## Story 1.4: 交易员-电站与运维员-设备绑定配置

As a 系统管理员（老周）,
I want 配置交易员与电站的绑定关系、储能运维员与储能设备的绑定关系,
So that 每个人只能操作和查看自己负责的电站/设备。

**Acceptance Criteria:**

**Given** 管理员已登录且系统中已有用户和电站数据
**When** 管理员为一个交易员选择一个或多个电站并保存绑定关系
**Then** 绑定关系生效，该交易员登录后仅能看到绑定电站的数据，绑定变更记录写入审计日志

**Given** 管理员已登录且系统中已有运维员角色用户和储能设备数据
**When** 管理员为一个储能运维员选择一个或多个储能设备并保存绑定关系
**Then** 绑定关系生效，该运维员仅能查看和操作所绑定设备的调度指令，绑定变更记录写入审计日志

**Given** 交易员已绑定电站A和电站B
**When** 管理员移除交易员与电站B的绑定
**Then** 交易员下次访问时无法看到电站B的数据，变更记录写入审计日志

---

## Story 1.5: 数据访问权限控制

As a 系统用户,
I want 系统根据我的角色和绑定关系自动过滤我能看到的数据,
So that 我只能访问权限范围内的信息，符合数据安全要求。

**Acceptance Criteria:**

**Given** 交易员登录后
**When** 访问任何包含电站数据的API端点
**Then** 仅返回该交易员已绑定电站的数据，未绑定电站数据不可见

**Given** 储能运维员登录后
**When** 访问储能调度相关API端点
**Then** 仅返回该运维员已绑定储能设备的数据

**Given** 交易主管登录后
**When** 访问电站数据API
**Then** 可查看所有电站的数据（不受绑定限制）

**Given** 高管只读角色用户登录后
**When** 尝试执行写操作（如修改报价、提交确认）
**Then** 系统返回403权限不足错误

**Given** 未认证用户
**When** 直接访问任何API端点（不携带Token）
**Then** 系统返回401未认证错误

---
