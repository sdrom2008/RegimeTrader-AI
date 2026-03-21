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
- **项目: NexusAI Tech (AI营销SaaS平台) 开发**
    - **状态**: ✅ **后端核心功能全部完成（编译通过）**
    - **已完成**:
        - 修复代码结构：分离接口与DTO，重建 `IConversationRepository`
        - 修复所有 using 引用，解决类型未找到错误
        - 修复 `ChatIntent` 枚举缺失别名问题（添加 `QueryOrder`/`QueryLogistics`）
        - 注册 `SemanticKernelService` 解决 DI 错误
        - 安装 .NET SDK 10.0，成功构建解决方案
        - 实现核心 Agent：
            - `ProductOptimizationAgent` - 商品优化（标题、详情、营销方案、图片 prompt）
            - `CompetitorAnalysisAgent` - 竞品分析
        - 更新 `AgentController` 支持商品优化（调用 Agent）
        - 新增 `CompetitorAnalysisController` - 专用竞品分析 API（`POST /api/competitor/analyze`）
        - 扩展 `ChatContext` DTO 加入商品信息字段
        - 扩展 `IAgentRouter` 接口，新增 `RouteAsync` 方法简化 Agent 调用
        - 清理重复文件
        - GitHub 提交：8281fda → 80a7bb1 → 9c24078 → 44b9564
    - **API 端点清单**:
        - `POST /api/marketing/generate-copy` - 营销文案生成
        - `POST /api/chat/send` - 客服对话
        - `POST /api/agent/optimizeproduct` - 商品优化
        - `POST /api/competitor/analyze` - 竞品分析
    - **当前行动**: ✅ 本地测试后端 API（基础验证完成）
        - ✅ 编译成功（.NET 10）
        - ✅ 服务启动正常（监听 5145）
        - ✅ 基础端点 /weatherforecast 正常
        - ✅ 营销端点 /api/marketing/generate-copy 路由与参数验证正常（需真实 AI Key 调用生成）
        - ⚠️ Chat 端点需配置：JWT Key + MySQL + Tongyi API Key
        - ✅ 已创建 `appsettings.Development.json` 开发配置模板（占位符）
        - ✅ 临时禁用微信支付（避免证书依赖导致启动失败）
        - ⏸️ 待配置真实环境变量后进行完整 API 测试
    - **待完成（前端）**:
        - 核心页面：营销文案生成、客服对话、商品优化、竞品分析
        - UI 美化（Ant Design Vue）
        - 部署文档（配置模板、环境变量说明）
    - **下一步**: 前端开发 + 联调，完成后内部测试

- **项目: RegimeTrader AI (量化交易) v1**
    - **状态**: ✅ **运行中 (模拟盘验证阶段)**
    - **已完成**:
        - 修复 `paper_trader.py` 资金管理模型（开仓扣保证金、平仓返还保证金、计盈亏、手续费处理）
        - 统一实盘/模拟逻辑：`live_executor.py` (DRY_RUN=1) 调用 `paper_trader`
        - 修复 `live_multi_hedge_engine.py` 权益计算（含未实现盈亏）
        - 修复 WhatsApp 通知（绝对路径 + DRY_RUN 跳过）
        - 调整报告频率：执行器每小时整点发送，绩效分析器每小时第5分钟发送
        - 配置参数：扫描前60个币种，AI趋势 + MarketStateAnalyzer.conf≥0.7，3倍杠杆，5%风险，ATR×1.5止损
        - 系统已通过 crontab 自动运行（每5分钟扫描，每小时整点执行器报告+第5分钟绩效报告）
        - 新增 `performance_analyzer.py` - 自动生成详细绩效报告（Markdown）+ WhatsApp摘要
        - 打包 v1.2：`regimetrader_ai_product_20260317_1627.tar.gz`
        - **修复关键Bug**: 闭仓返还保证金，确保总资产计算准确
    - **当前状态** (07:05 UTC, 3月18日):
        - 总资产 $11,018 (+10.18%)
        - 持仓2个（OPN/USDT浮盈+$187, ZEC/USDT浮盈+$264）
        - 已平仓3笔，胜率 100%（样本太小，需继续积累）
    - **下一步**:
        - 继续自动运行，等待积累至少20-30笔平仓交易
        - 样本充足后评估：胜率、盈亏比、最大回撤
        - 决定：实盘部署 / 参数调优 / 模型重新训练

- **项目: RegimeTrader AI v2 (优化版 - 双向交易 + 6年数据)**
    - **状态**: 🔄 **P1 正式干跑（60 币种，dry-run）**
    - **架构升级**:
        - ✅ 三分类模型（`强涨/强跌/震荡`）支持双向交易
        - ✅ 方向特征：`+DI/-DI`, `MACD_hist`, `Price_vs_EMA200`, `Volume_Change_Ratio`
        - ✅ 动态标签：滚动分位数阈值（适应不同波动）
        - ✅ 增强统计特征：价格滚动波动率、ATR比率、20周期回撤、RSI偏离
    - **基础设施 (P0 完成)**:
        - ✅ 配置分离：`config.py` 统管所有参数
        - ✅ 日志系统：`logger_v2.py`（分级日志 + 文件轮转）
        - ✅ 状态隔离：`paper_trade_state_v2.json` 独立存储
        - ✅ 执行器重构：`paper_trader.py`（含错误处理 + WhatsApp 通知）
    - **模型训练**:
        - ✅ 6年数据下载完成（BTC/USDT 1h，52,536行，2020-2026）
        - ✅ 单币种训练：`regime_model_v2_quantile.pkl` (50 MB, RandomForest 300 trees)
        - ⏳ **多币种联合训练** (进行中):
          - 数据: BTC, ETH, BNB, SOL, XRP (各 6年 1h)
          - 总样本 ~26 万
          - 脚本: `train_model_v2_multi.py`
          - 新模型: `regime_model_v2_multi.pkl`
        - 📊 特征重要性（BTC单币）: DI_diff (29.4%), ADX (19.9%), +DI (8.9%), -DI (8.8%), ADX_weak (8.5%)
    - **参数优化**:
        - ✅ 验证集搜索最优 `(ADX_thresh, conf_thresh)` → ADX>=25, CONFIDENCE>=0.60
        - ✅ 效果：准确率 85.8%，Up/Down 召回率 85.1%
    - **信号验证**:
        - ✅ 20币种扫描（ADX>=25, conf>=0.60）：4个高质量 BUY 信号（BTC/BNB/PEPE/SUI）
        - ✅ 无空头信号（当前市场多头阶段，机制正常）
    - **风控参数**:
        - LEVERAGE = 2.5x
        - RISK_PER_TRADE_PCT = 5%（已调整，支持多持仓）
        - STOP_LOSS_ATR_MULT = 2.0
        - TAKE_PROFIT_RR = 2.0
        - TRAILING_STOP_ATR = 1.5
        - TRADING_SYMBOLS = ['BTC/USDT','ETH/USDT','BNB/USDT','SOL/USDT','XRP/USDT']（仅交易训练币种）
    - **代码状态**:
        - ✅ v2 主版本：`config.py`, `paper_trader.py`, `live_executor.py`
        - ✅ v1 已归档至 `legacy/v1/`
        - ✅ 宏风险监控模块已禁用（待测试恢复）
        - ✅ 白名单过滤已添加（仅交易训练币种）
    - **当前运行**:
        - ✅ `live_executor.py` 运行中 (PID 761716)
        - ✅ 持仓: NIGHT/USDT BUY (浮亏)
        - ✅ 多持仓验证：正常（5% risk，balance: $1709, margin: $8159）
    - **待完成 (P1)**:
        - 🔄 **多币种训练** (进行中，PID 773228) → 生成 `regime_model_v2_multi.pkl`
        - [ ] 训练完成后：更新 `config.py` 的 `MODEL_FILE` 指向新模型
        - [ ] 重启 v2，评估性能表现
        - [ ] 积累 30-40 笔交易后评估指标（胜率、盈亏比、最大回撤、夏普）
        - [ ] 确认表现良好后设定 cron 自动化
    - **风险提示**: v2 重大升级，务必充分验证后再实盘

- **战略思考: SaaS 产品演进 (OpenClaw 时代)**
    - **背景**: OpenClaw 的成功表明下一代软件是 "AI Agent + 工具调用 + 记忆 + 自主规划"
    - **当前局限**: NexusAI Tech 仍是 "被动响应" 的 SaaS（表单/按钮点击）
    - **下一代方向**: 升级为 **"AI 主控 Agent + 子Agent 协作 + 工具自动执行"** 模式
    - **关键特性**:
        1. 对话式入口（自然语言描述需求）
        2. 主控 Agent 任务分解与调度
        3. 子 Agent 专业化（竞品分析、SEO、营销、客服等）
        4. 工具层集成（平台 API、设计工具、数据服务）
        5. 长期记忆（商家偏好、历史决策、效果数据）
        6. 自动化执行（从分析到方案再到实施，一键完成）
    - **行动项**:
        - [ ] 将现有 Service 封装为 Agent（实现 `IAgent` 接口）
        - [ ] 设计并实现 `MainAgent`（任务理解与规划）
        - [ ] 定义工具接口（Tool Calling 规范）
        - [ ] 集成向量数据库（LanceDB）用于知识检索
        - [ ] 前端改造为对话式交互（类似 ChatGPT）
    - **优先级**: P1（在 MVP 前端完成后启动）

已完成历史（最近5条）：
- **完成量化交易项目**: 成功交付了AI驱动的量化交易引擎 "阿尔法猎手" v1.0，并为其设置了自动化模拟运行。
- **创建协同代理**: 成功创建了虾米1号（编程）、虾米2号（测试）和旧虾米3号（复盘总结）三个子代理，用于量化交易项目。
- **Solana Backend Rebuild Bounty**: 已标记为过期和无效。
- **创建产品文件夹与PRD**: 创建了 `regime_trader_ai_product` 文件夹，并保存了 PRD 草稿 `regime_trader_ai_product/PRD_draft.md`。
- **代理任务模式调整**: 调整代理创建模式为 `mode="run"`，并更新任务描述以使用共享工作空间。
