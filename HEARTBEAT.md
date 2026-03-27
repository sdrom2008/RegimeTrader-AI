1. **Token 节省**: 严格遵守 800k 上下文限制。每次任务完成后立即汇总进度并建议 `/reset`。
2. **随时更新HEARTBEAT.md**: 这个文件是让你规划任务的，当前任务清单，都由你思考后更新，能保证你持续更新任务，不重复做事。

# 💓 HEARTBEAT Tasks - 严格执行，不要重复旧任务

每心跳（默认20m）必须做：
核心指令（每次心跳必读）：
- 优先读 SOUL.md → AGENTS.md → MEMORY.md → 本文件
- 如果有最高优先任务，拆成 1-3 步小行动，用工具执行
- 每步后：更新本文件（打勾、写结果、加新子任务或删除完成项）
- 如果无事可做 → 回复 HEARTBEAT_OK（静默）
- 如果任务卡住/需要我 → 发简短消息给我 + 暂停该任务
- 永远优先低成本行动（先读文件/本地检查，再 web/LLM）
- 禁止高危：删系统文件、发邮件不经确认、泄露凭证

当前任务清单：
- **项目: NexusAI Tech (AI营销SaaS平台) - Phase 1 MVP 剩余开发**
    - **状态**: ✅ **多角色架构完成，API运行于7092，前端页面已改造（2026-03-22）**
    - **蓝图文档**: `NEXUSAI_FULL_BUSINESS_LOGIC.md`
    - **核心目标**: 4周内完成MVP可演示版本（包含客服工作台+主管面板+卖家Dashboard）
    - **P0 任务清单**:
        - [x] **登录系统**（后端JWT + 前端登录页）- AuthController已实现，手机验证码登录可用
        - [x] **卖家Dashboard**（/dashboard 页面 + API）- 对接 `/api/seller/profile`
        - [x] **客服工作台**（/support/workbench 页面 + API）- 三栏布局，对接 tickets/messages/reply
        - [x] **主管监控面板**（/support/supervisor 页面 + API）- 对接 dashboard 和 agents/stats
        - [x] **会话管理**（ChatSessions 表 + 业务逻辑）- Entity + Service
        - [x] **客服管理API**（agents, stats, assignment）- SupportController完成
        - [x] **路由守卫与权限控制** - [Authorize]已应用
        - [x] **数据库表结构修复**（2026-03-22）: 修复 CustomerId 类型、新增 chat_messages 表、添加 EnsureCreated 自动建表
        - [x] **多角色身份体系**（2026-03-22）: 区分 Seller/Agent/Supervisor，新增 MerchantController
        - [x] **前端页面改造**（2026-03-22）: 商户会话列表、客服工作台、主管面板，适配新接口
    - **阻塞**: 无（开发环境已就绪）
    - **下一步**: 
        - [x] **国际化手机号登录** - 支持国家选择器，后端接受 CountryCode
            - [x] 修改 AuthDTOs：PhoneLoginDto/SendCodeDto/BindPhoneDto 增加 CountryCode
            - [x] 修改 AuthController：SendCode/PhoneLogin/BindPhone/DecryptPhone 使用完整国际格式
            - [x] 前端 login.vue：添加国家选择器，移除11位限制
            - [x] 提交 GitHub: 8d1948c
        - [x] **多语言界面** - 支持中英文切换（i18n）
            - [x] 创建语言包（zh-CN, en-US）
            - [x] 实现 i18n 工具
            - [x] 添加语言切换按钮（login.vue）
            - [x] 添加 Footer 显示 ICP 备案号：湘ICP备2026009564号
            - [x] 翻译核心页面：login, choose-login, shop-setting, sessions, workbench, supervisor
            - [x] 提交 GitHub: ffa7353, 837c86a, b592eea, 849f39a
        - [ ] **全流程集成测试**（商户 → 客服工作台 → 主管面板）- **待用户执行**
        - [ ] **Shopee平台对接** - 电商平台中最友好，无国内资质要求
            - [x] 创建 `ShopeePlatformClient` 骨架（签名/解析占位）
            - [x] 创建 `PlatformClientRouter` 路由工厂
            - [x] 改造 `WebhookController` 为通用平台接入
            - [x] Program.cs 注册所有客户端
            - [x] 编译通过
            - [x] 修复 `ChatMessage.FromAI` 参数编译错误
            - [x] 实现模拟端点 `/api/webhook/shopee/test`
            - [x] 创建部署脚本 `start-api.sh`
            - [x] 编写部署指南 `DEPLOYMENT.md`
            - [x] 实现 Shopee 签名验证逻辑（HMAC-SHA256）
            - [x] 实现 Webhook 消息解析（聊天推送）
            - [x] 实现消息发送 API 调用（签名+HTTP POST）
            - [ ] 配置 `appsettings.json`（AppKey/Secret/ShopID/AccessToken）
            - [ ] 公网 Webhook URL 配置（ngrok/域名）
        - [x] **Windows Server 2022 部署方案** - ✅ 用户已成功部署并反馈（2026-03-27）

- **项目: RegimeTrader AI v2 (优化版 - 双向交易 + 6年数据)**
    - **状态**: ✅ **已重新训练完成（2026-03-24）** - 修复标签泄漏 bug
    - **架构升级**:
        - ✅ 三分类模型支持双向交易
        - ✅ 方向特征、动态标签
        - ✅ 配置分离、日志系统、状态隔离
    - **模型训练**:
        - ✅ 6年数据下载完成
        - ✅ 单币种训练完成
        - ✅ 多币种联合训练完成（259,120样本，86%准确率）
        - ✅ v2 代码优化提交 + 文档更新
    - **参数调整**（2026-03-24）:
        - ✅ 放开白名单：扫描全部60个币种
        - ✅ 降低 ADX 阈值：23 → 20
        - ✅ 降低置信度：0.60 → 0.55
    - **风控**: LEVERAGE=2.5x, RISK=5%
    - **当前运行**: live_executor.py (NEAR/USDT 空头持仓，08:16 UTC 开仓)
    - **下一步**:
        - [ ] 继续运行，积累20-30笔交易
        - [ ] 绩效分析（胜率、盈亏比、最大回撤）
        - [ ] 评估是否投入真实资金

- **战略思考: SaaS 产品演进 (OpenClaw 时代)**
    - **方向**: 升级为 **"AI 主控 Agent + 子Agent 协作 + 工具自动执行"** 模式
    - **行动项**:
        - [ ] 将现有 Service 封装为 Agent
        - [ ] 设计并实现 `MainAgent`
        - [ ] 定义工具接口（Tool Calling）
        - [ ] 集成向量数据库（LanceDB）
        - [ ] 前端改造为对话式交互
    - **优先级**: P1（MVP 前端完成后启动）

已完成历史（最近5条）：
- **NexusAI Tech 业务逻辑梳理完成**: 创建 NEXUSAI_FULL_BUSINESS_LOGIC.md，完整定义Phase 1-3开发蓝图
- **NexusAI Tech 前端完成**: 成功完成前端UI/UX全面优化（4个核心页面）并构建成功，可部署。
- **创建协同代理**: 成功创建虾米1号（编程）、虾米2号（测试）和旧虾米3号（复盘总结）三个子代理，用于量化交易项目。
- **NexusAI Tech 后端编译通过**: 修复所有代码结构问题，.NET 10 环境搭建完成，API 端点就绪。
- **完成量化交易项目**: 成功交付"阿尔法猎手" v1.0。
