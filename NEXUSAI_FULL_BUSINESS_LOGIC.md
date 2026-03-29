# NexusAI Tech - 完整业务逻辑与系统设计

**版本**: 1.0  
**日期**: 2026-03-21  
**作者**: 虾子（AI Assistant）  
**状态**: 项目推进蓝图

---

## 📌 文档说明

本文档定义NexusAI Tech的完整业务逻辑、系统架构、用户角色、功能模块、API设计、数据库表结构及分阶段开发计划。作为项目推进的**唯一蓝图**，所有开发任务均以本文档为准。

---

## 一、用户角色体系（5类）

| 角色 | 描述 | 登录入口 | 核心需求 |
|------|------|----------|----------|
| **买家** | 电商平台的消费者 | 淘宝/京东聊天窗口（无Nexus账号） | 快速咨询、秒回、解决问题 |
| **卖家老板** | 购买NexusAI SaaS的商家 | NexusAI卖家工作台（主账号） | 管理团队、监控数据、付费订阅 |
| **客服人员** | 卖家雇佣的客服 | NexusAI客服工作台（子账号） | 处理AI转交的对话、服务客户 |
| **客服主管** | 管理客服团队 | NexusAI主管工作台（权限更高） | 分配会话、质检、绩效统计 |
| **系统管理员** | NexusAI内部人员 | 后台管理系统 | 用户管理、系统监控、计费 |

**注意**：买家不需要NexusAI账号，他们只在电商平台聊天。其他4类用户在NexusAI平台有账号。

---

## 二、功能模块与页面清单（总计8个页面）

### A. 卖家工作台（Seller Dashboard）

**使用者**：卖家老板

**页面列表**：
1. **登录页**（/login）：卖家老板登录入口
2. **总览Dashboard**（/dashboard）：
   - 本月数据：对话量、AI解决率、节省人力成本
   - 订阅状态（套餐类型、剩余次数）
   - 快捷入口：AI测试、客服管理、数据报表
3. **客服团队管理**（/support/agents）：
   - 添加/删除客服账号
   - 设置客服权限
   - 在线状态监控
4. **数据报表**（/reports）：
   - 对话量趋势
   - AI与人工占比
   - 客服绩效排行榜
   - 导出Excel

### B. AI测试与演示（已部分完成）

5. **AI测试界面**（/chat）✅ 已有：
   - 模拟买家与AI对话
   - 查看意图识别结果
   - 测试回复质量

**用途**：卖家老板或运营测试AI效果

### C. 人工客服工作台🆕（新设计）

6. **客服工作台**（/support/workbench）：
   - 会话列表（待处理/进行中/已结束）
   - 客户信息侧边栏
   - 对话窗口
   - 快捷回复库
   - 查看订单/商品信息

**使用者**：客服人员

### D. 主管管理面板🆕（新设计）

7. **主管监控面板**（/support/supervisor）：
   - 实时队列（待处理对话数、平均等待时长）
   - 客服在线状态与负载
   - 会话分配（手动分配或自动分配规则）
   - 质检对话（查看、评分、标记案例）
   - 团队绩效报表

**使用者**：客服主管

### E. 后台管理（可选，Phase 3）

8. **系统管理后台**（/admin）：
   - 用户管理（所有卖家、客服）
   - 订阅管理（套餐、付费）
   - 系统监控（API调用量、错误日志）
   - FAQ知识库管理
   - 意图分类模型管理

---

## 三、完整业务流程（End-to-End）

### 业务流程1：买家咨询 → AI自动回复

```
1. 买家在淘宝店铺聊天窗口输入：
   "我的订单12345发货了吗？"

2. 淘宝平台 → 调用NexusAI API
   POST /api/chat/send
   {
     "customerId": "淘宝用户ID",
     "message": "我的订单12345发货了吗？",
     "shopId": "店铺ID"
   }

3. NexusAI系统处理：
   a. 意图识别：LogisticsQuery
   b. 查询订单系统（通过shopId找到对应店铺的订单API）
   c. 生成回复："订单已发货，快递单号SF123456，预计3天内到达"

4. 返回给淘宝平台 → 买家看到回复

5. 系统记录：
   - 对话存入数据库（Conversations表）
   - 会话ID（SessionId）关联客户
   - 统计：AI解决、无人工介入
```

---

### 业务流程2：AI转人工

```
1. AI处理上述对话后：
   - 意图识别：Complaint（投诉）
   - 置信度：60%（低于阈值70%）
   - 或检测到负面情绪（"气死我了"、"投诉"关键词）

2. 系统自动：
   a. 创建待处理会话，状态="pending"
   b. 根据规则分配客服：
      - 负载均衡：选在线客服中会话最少的
      - 技能匹配：投诉类分配给售后客服
   c. 通知客服（工作台刷新、声音提醒）

3. 客服A在NexusAI工作台看到：
   【待处理队列】
   - 客户：张三（淘宝昵称）
   - 问题类型：投诉
   - 等待时长：2分钟
   - 对话预览："订单12345发货了吗？...气死我了"

4. 客服A点击"接管"：
   - 会话状态变为"active"
   - 分配客服ID = A
   - 工作时间戳开始

5. 客服A在NexusAI工作台回复：
   "您好，非常抱歉给您带来不好的体验，请提供订单号我立刻为您查询..."

6. 回复通过API返回淘宝 → 买家收到

7. 客服解决后，标记会话为"resolved"
   - 记录解决时长、客户满意度（后续邀请评价）
```

---

### 业务流程3：卖家老板监控

```
1. 老板登录NexusAI卖家工作台

2. Dashboard显示：
   - 今日接待客户数：156
   - AI自动解决率：78%
   - 平均响应时间：12秒
   - 节省客服人力：≈3人
   - 本月费用：¥599（专业版）

3. 点击【客服团队管理】：
   - 在线客服：3人（张三、李四、王五）
   - 今日接待量：张三45, 李四38, 王五32
   - 平均响应时长：张三8秒, 李四12秒, 王五15秒

4. 点击【数据报表】：
   - 导出本周对话记录
   - 查看AI意图识别准确率报表（92%）
   - 发现"退款"意图识别率低 → 决定优化FAQ
```

---

## 四、系统架构与数据流

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层（Vue 3）                       │
├─────────────────────────────────────────────────────────────┤
│ /login                   - 卖家登录                           │
│ /dashboard              - 卖家Dashboard                      │
│ /support/agents         - 客服管理                           │
│ /reports               - 数据报表                            │
│ /chat                  - AI测试界面 ✅                       │
│ /support/workbench     - 客服工作台 🆕                       │
│ /support/supervisor    - 主管面板 🆕                        │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP API
┌─────────────────────────────────────────────────────────────┐
│                    API网关层（.NET）                         │
├─────────────────────────────────────────────────────────────┤
│ 认证：JWT Token（不同角色权限不同）                          │
│ 路由：基于角色和路径分发请求                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ 会话管理      │ 意图识别      │ 客服管理      │ 数据统计      │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ - /chat/send │ - Intent API │ - /support/* │ - /reports/* │
│ - /sessions  │ - FAQ Match  │ - /agents    │ - /analytics │
│ - History    │ - LLM Call   │ - Queue      │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 数据层 & 外部系统                           │
├─────────────────────────────────────────────────────────────┤
│ 数据库（MySQL）：                                             │
│   Users（卖家、客服账号）                                     │
│   Conversations（对话记录）                                  │
│   ChatSessions（会话状态）                                   │
│   Orders（订单对接缓存）                                      │
│                                                                 │
│ 外部API：                                                     │
│  电商平台API（淘宝/京东订单查询、物流）                       │
│  LLM API（意图识别、回复生成）                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、详细的API清单（扩展版）

### 🔐 认证相关
```
POST /api/auth/login          # 登录（卖家、客服、主管）
POST /api/auth/logout         # 登出
GET  /api/auth/me             # 获取当前用户信息
```

### 💬 客服对话相关
```
POST /api/chat/send           # 发送消息（买家→AI，现有）
GET  /api/chat/history        # 获取对话历史（按customerId）
POST /api/chat/transfer       # 转人工（指定客服）
GET  /api/chat/sessions       # 获取会话列表（客服/主管视角）
```

### 🤖 AI相关
```
POST /api/ai/identify-intent  # 意图识别（内部调用）
POST /api/ai/generate-reply   # 生成回复（基于FAQ或LLM）
GET  /api/ai/faq              # 获取FAQ列表（知识库）
```

### 👥 客服工作台相关
```
GET  /api/support/tickets     # 获取待处理队列（客服列表）
POST /api/support/tickets/{id}/take    # 客服接管会话
POST /api/support/tickets/{id}/reply   # 客服发送回复
POST /api/support/tickets/{id}/resolve # 标记解决
GET  /api/support/customer/{id}        # 获取客户信息（订单、标签）
GET  /api/support/quick-replies        # 获取快捷回复模板
```

### 🎛️ 主管管理相关
```
GET  /api/support/agents             # 客服列表
GET  /api/support/agents/{id}/stats  # 客服绩效统计
POST /api/support/assign             # 手动分配会话
GET  /api/support/quality            # 质检对话列表
POST /api/support/quality/{id}/review # 提交质检评分
```

### 📊 数据报表相关
```
GET  /api/reports/dashboard         # Dashboard数据聚合
GET  /api/reports/conversations     # 对话量统计（按时间）
GET  /api/reports/ai-performance    # AI性能报表（准确率、解决率）
GET  /api/reports/agent-performance # 客服绩效报表
```

### ⚙️ 卖家管理相关
```
GET  /api/seller/profile            # 卖家信息
PUT  /api/seller/profile           # 更新设置
GET  /api/seller/subscription      # 订阅状态
POST /api/seller/subscription/upgrade # 升级套餐
GET  /api/seller/team              # 客服团队列表
POST /api/seller/team/invite       # 邀请客服
```

---

## 六、数据库表设计（关键表）

### 1. Users（用户表）
```sql
CREATE TABLE Users (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    Email VARCHAR(255) UNIQUE,
    PasswordHash VARCHAR(255),
    Name VARCHAR(100),
    Role ENUM('Seller', 'Agent', 'Supervisor', 'Admin'),
    ShopId INT NULL,
    IsActive BOOLEAN DEFAULT true,
    CreatedAt DATETIME
);
```

### 2. Shops（店铺表）
```sql
CREATE TABLE Shops (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(200),
    OwnerId INT ( SellerId ),
    Plan ENUM('Basic', 'Pro', 'Enterprise'),
    ApiKey VARCHAR(100),
    ApiSecret VARCHAR(200),
    IsActive BOOLE DEFAULT true,
    FOREIGN KEY (OwnerId) REFERENCES Users(Id)
);
```

### 3. Conversations（对话记录表）
```sql
CREATE TABLE Conversations (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    SessionId VARCHAR(100),
    CustomerId VARCHAR(200),
    CustomerName VARCHAR(200),
    ShopId INT,
    Platform ENUM('Taobao', 'JD', 'Douyin', 'Other'),
    Intent VARCHAR(50),
    Confidence FLOAT,
    IsResolved BOOLEAN DEFAULT false,
    CreatedAt DATETIME
);
```

### 4. ChatMessages（消息明细表）
```sql
CREATE TABLE ChatMessages (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    ConversationId INT,
    Role ENUM('User', 'Assistant', 'Agent'),
    Content TEXT,
    Timestamp DATETIME,
    AgentId INT NULL,
    FOREIGN KEY (ConversationId) REFERENCES Conversations(Id),
    FOREIGN KEY (AgentId) REFERENCES Users(Id)
);
```

### 5. ChatSessions（会话状态表）🆕
```sql
CREATE TABLE ChatSessions (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    SessionId VARCHAR(100) UNIQUE,
    CustomerId VARCHAR(200),
    ShopId INT,
    Status ENUM('Pending', 'Active', 'Resolved', 'Closed'),
    AssignedAgentId INT NULL,
    AssignedAt DATETIME NULL,
    ResolvedAt DATETIME NULL,
    Satisfaction TINYINT NULL,
    FOREIGN KEY (AssignedAgentId) REFERENCES Users(Id)
);
```

### 6. Orders（订单缓存表）🆕
```sql
CREATE TABLE Orders (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    ShopId INT,
    OrderNo VARCHAR(100),
    CustomerId VARCHAR(200),
    Status VARCHAR(50),
    TotalAmount DECIMAL(10,2),
    LogisticsNo VARCHAR(100),
    CreatedAt DATETIME,
    FOREIGN KEY (ShopId) REFERENCES Shops(Id)
);
```

### 7. QuickReplies（快捷回复模板）🆕
```sql
CREATE TABLE QuickReplies (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    ShopId INT,
    Category VARCHAR(50),
    Title VARCHAR(200),
    Content TEXT,
    IsActive BOOLEAN DEFAULT true,
    FOREIGN KEY (ShopId) REFERENCES Shops(Id)
);
```

---

## 七、分阶段开发计划（Roadmap）

### Phase 1：MVP核心（4周）✅ 部分完成
**目标**：NexusAI基础SaaS可演示

**已完成（60%）**：
- 后端API：营销文案、商品优化、竞品分析 ✅
- 前端：营销、优化、竞品、AI测试页面 ✅
- 构建部署：前端构建成功 ✅

**待完成（40%）**：
1. **登录系统**（卖家、客服统一登录，JWT） - 1周
2. **卖家Dashboard**（总览、快捷入口） - 0.5周
3. **客服工作台**（会话列表、对话窗口） - 1.5周
4. **主管监控面板**（队列、绩效、质检） - 1周
5. **后端API扩展**（会话管理、客服管理、报表） - 1周

**Phase 1完成标志**：
- 卖家老板可登录，看到Dashboard
- 客服可登录工作台，接收并处理对话
- 主管可监控团队绩效
- 完整演示可用

---

### Phase 2：真实对接（4周）
**目标**：对接真实电商平台，AI意图识别准确率>90%

**任务**：
1. 对接淘宝开放平台API（订单查询、物流）
2. 对接京东联盟API
3. 训练意图识别模型（基于真实对话数据）
4. FAQ知识库管理后台
5. AI客服准确率优化（收集bad cases）

**完成标志**：真实店铺可接入使用

---

### Phase 3：增值功能（3周）
**目标**：增加付费点，提升ARPU

**任务**：
1. 数据报表高级功能（导出、自定义）
2. 批量操作（批量商品优化、批量客服话术）
3. 多语言支持（英文、东南亚）
4. API开放平台文档
5. 客户成功案例库

---

## 八、关键业务规则

### 规则1：会话分配策略
- **自动分配**：新对话分配给"最闲"的在线客服（会话数最少）
- **技能匹配**：投诉类分配给售后客服，咨询类分配给售前客服
- **VIP客户**：分配给专属客服（标记VIP的客户）

### 规则2：转人工条件
- AI置信度 < 70%
- 意图 = `Complaint` | `Refund` | `QualityIssue`
- 客户明确要求"转人工"
- AI连续3次无法回答

### 规则3：客服工作流程
- 客服登录后，状态="Online"
- 系统自动推送待处理对话（声音+红点）
- 客服必须在5分钟内"接管"（SLAs）
- 对话超时30分钟未解决，自动转交其他客服

### 规则4：计费模式（待定）
- 平台按"对话量"计费还是按"客服席位数"计费？
- AI对话是否计入套餐？
- 人工客服是否额外收费？

---

## 九、当前项目状态（2026-03-21）

### ✅ 已完成组件
- [x] 后端：营销文案、商品优化、竞品分析API（.NET 10）
- [x] 前端：4个核心页面（Marketing, Chat, Product, Competitor）
- [x] 前端构建成功（dist/生成）
- [x] API配置：`http://192.168.1.254:7092`

### 🔄 需改造/新增组件
- [ ] **登录系统**：JWT认证、角色权限
- [ ] **卖家Dashboard**：/dashboard 页面 + API
- [ ] **客服工作台**：/support/workbench（全新设计）
- [ ] **主管监控面板**：/support/supervisor（全新设计）
- [ ] **客服管理**：/support/agents 页面 + API
- [ ] **数据报表**：/reports 页面 + API
- [ ] **会话管理**：ChatSessions表 + 相关业务逻辑
- [ ] **快捷回复**：QuickReplies表 + 管理功能

### 📋 待办任务清单（按优先级）

**P0 - 必须完成（Phase 1 MVP）**：
1. 设计并开发登录页面（/login）
2. 实现JWT认证中间件（后端）
3. 设计卖家Dashboard页面（/dashboard）
4. 实现卖家Dashboard相关API
5. 设计客服工作台UI/UX（线框图 → 代码）
6. 开发客服工作台前端（/support/workbench）
7. 实现客服工作台API（tickets, take, reply, resolve）
8. 实现ChatSessions会话状态管理
9. 设计主管监控面板UI（/support/supervisor）
10. 开发主管面板前端 + API
11. 实现客服列表与绩效统计API
12. 路由守卫与权限控制（前端）

**P1 - Phase 1 补充**：
13. 客服团队管理页面（/support/agents）
14. 数据报表页面（/reports）
15. 快捷回复功能（前端组件 + 后端API）
16. 客户信息侧边栏（订单历史显示）
17. 全局状态管理（Pinia）优化
18. 错误处理与用户提示统一

**P2 - Phase 2 准备**：
19. 意图识别模型训练（数据收集、标注）
20. FAQ知识库管理后台
21. 电商平台API对接（淘宝、京东）
22. AI准确率优化迭代

---

## 十、下一步行动（ Immediate Next Steps）

### 今天/明天（2026-03-21 ~ 03-22）

**后端任务**：
1. [ ] 创建数据库迁移脚本（新增5张表）
2. [ ] 实现JWT认证（AuthController + Middleware）
3. [ ] 实现Users表CRUD（客服管理用）
4. [ ] 实现ChatSessions会话管理API
5. [ ] 实现Support Tickets API（GET /tickets, POST /take, POST /reply）

**前端任务**：
1. [ ] 设计登录页面UI（简洁、支持角色选择）
2. [ ] 设计卖家Dashboard线框图
3. [ ] 设计客服工作台详细UI（三栏布局）
4. [ ] 设计主管监控面板UI
5. [ ] 配置路由守卫（未登录重定向、权限校验）

**协作任务**：
1. [ ] 确认业务规则（会话分配、转人工条件、计费模式）
2. [ ] 确定API接口详细规范（请求/响应格式）
3. [ ] 建立数据库连接字符串配置

---

**文档结束**

**行动原则**：按本蓝图分阶段推进，每完成一个阶段进行复盘和调整。Phase 1目标：4周内完成MVP可演示版本。
