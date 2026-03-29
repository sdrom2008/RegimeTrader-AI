
## Memory Management Guidelines for Documentation & Upgrades

To ensure comprehensive tracking of our projects, the following formats are recommended for documenting products and their upgrades:

### Product Documentation Format:
```markdown
## Product: [Product Name]
*   **Description**: [Brief overview of the product]
*   **Core Functionalities**:
    *   [Functionality 1]
    *   [Functionality 2]
    *   ...
*   **Key Components/Files**:
    *   [File Path 1]
    *   [File Path 2]
    *   ...
*   **Related Bounties/Tasks**: [Link to related tasks, e.g., bounty ID]
*   **Status**: [e.g., Development, Testing, Deployed, Obsolete]
*   **Documentation Link (if applicable)**: [Link to external or internal docs]
```

### Upgrade Records Format:
```markdown
## Upgrade Log for [Product Name]
*   **Version**: [Version Number or Date]
*   **Date**: [YYYY-MM-DD]
*   **Description of Changes**:
    *   [Summary of changes, e.g., Added new feature X, Fixed bug Y, Improved performance Z]
*   **Impact**: [How the upgrade affects functionality or performance]
*   **Related Task/Bounty**: [Link to the task or bounty this upgrade relates to]
```

These formats should be used when documenting new products or logging significant upgrades to existing ones. Specific task details like links and deadlines should follow the 'Task Management Template' previously established.

## Product: NexusAI Tech (AI营销SaaS平台)
*   **Description**: AI-powered marketing SaaS platform for e-commerce sellers, providing automated copywriting, customer support, and product optimization.
*   **Core Functionalities**:
    *   Marketing copy generation (IMarketingCopyService)
    *   AI chat customer support with intent routing
    *   Product data management and standardization
*   **Key Components/Files**:
    *   `my-project/Synerixis.sln`
    *   `my-project/Synerixis.Application/` (services, interfaces, DTOs)
    *   `my-project/Synerixis.Domain/` (entities, enums, repositories interfaces)
    *   `my-project/Synerixis.Infrastructure/` (EF Core, external integrations)
    *   `my-project/Synerixis.Api/` (Web API)
*   **Status**: Development (backend MVP in progress)
*   **Notes**:
    *   Original code structure had interface definitions mixed with DTOs and implementations, causing compilation failures.
    *   Key fixes performed on 2026-03-16:
        - Separated `IMarketingCopyService` and moved DTOs to dedicated folder.
        - Created `Synerixis.Application.Interfaces.IConversationRepository` (inherits from `IRepository<Conversation>`), relocated from Domain to avoid circular dependencies.
        - Implemented missing repository methods: `GetByCustomerIdAsync`, `GetContextAsync`, `AppendMessagesAsync`, `SaveAsync`.
        - Fixed using directives across Infrastructure and API projects to resolve missing type errors.
        - Temporarily commented out `OrderAgent` and `LogisticsAgent` registrations due to interface mismatch (they need to implement `Synerixis.Application.Interfaces.IAgent` instead of the Agents-sub-namespace interface). This restores buildability; will address in a subsequent pass.
        - Overall project now compiles successfully with warnings only.
    *   Additional fix on 2026-03-17:
        - Resolved `ChatIntent` enum mismatch: added `QueryOrder` and `QueryLogistics` aliases to match `OrderAgent` and `LogisticsAgent` usage.
        - Installed .NET SDK 10.0 on environment and verified successful solution build (`dotnet build`).
    *   Next steps: Clean up redundant usings, ensure runtime behavior, align agent implementations.

## Upgrade Log for NexusAI Tech
*   **Version**: 2026-03-22（数据库修复）
*   **Date**: 2026-03-22
*   **Description of Changes**:
    *   Fixed `chat_sessions.CustomerId` type mismatch: changed from BINARY(16) to VARCHAR(100) to match entity definition.
    *   Added missing `chat_messages` table creation to migration script.
    *   Added `db.Database.EnsureCreated()` in Program.cs to auto-provision tables in development.
    *   Fixed `ILogger<>` missing using in GeneralChatAgent.
    *   Completed Database and Jwt configuration in appsettings files.
    *   Generated EF Core design-time factory and initial migration files for MySQL.
*   **Impact**: Resolved `SaveAsync` hang on first conversation due to missing tables and column type mismatch. API now starts on port 7092 and auto-creates all tables in development environment.
*   **Related Task**: Fix first-conversation crash in NexusAI Tech MVP.


## Upgrade Log for NexusAI Tech
*   **Version**: Strategic Pivot (Cross-Border E-Commerce)
*   **Date**: 2026-03-28
*   **Description of Changes**:
    *   **Business Pivot**: Moved away from domestic platforms (Taobao/JD) due to closed APIs and strict limits. Pivoting to cross-border e-commerce platforms (initially Shopee).
    *   **Feature Gap identified**: **Admin Backend (管理后台)** needs to be built for managing Sellers, Subscriptions, and Platform configurations.
    *   **Fixes applied**: Fixed WeChat login limitations on H5 (hidden via conditional compile), and implemented automatic Seller registration during Phone Login.
*   **Impact**: Focus shifted to integrating `ShopeePlatformClient`. Planning architecture for the new Admin Panel.

## Product: RegimeTrader AI (智能趋势跟踪量化交易系统)
*   **Description**: AI驱动的期货自动交易系统，基于机器学习识别市场状态（趋势/震荡），仅在趋势明确时开仓，配合3倍杠杆和ATR动态止损，实现风险可控的趋势跟踪。
*   **Core Functionalities**:
    *   AI 市场状态识别（RandomForest 分类器）
    *   双向交易（多/空）
    *   宏观过滤（情绪 + 多空比）
    *   固定风险仓位管理（每笔5%）
    *   ATR×1.5 移动止损
    *   模拟/实盘逻辑统一
    *   每小时自动报告（WhatsApp）
*   **Key Components/Files**:
    *   `regime_trader_ai_product/paper_trader.py` - 核心策略引擎
    *   `regime_trader_ai_product/live_executor.py` - 执行入口（模拟/实盘）
    *   `regime_trader_ai_product/code/market_state_logic.py` - 趋势分析器
    *   `regime_trader_ai_product/regime_model.pkl` - AI 模型
    *   `regime_trader_ai_product/paper_trade_state.json` - 模拟盘状态
*   **Status**: Testing (模拟盘自动运行中，验证盈利能力)
*   **Notes**:
    *   已完成模拟/实盘逻辑对齐，资金管理模型统一。
    *   修复：开仓扣除保证金、平仓计入盈亏和手续费、总资产正确计算。
    *   参数配置：扫描60个币种、置信度≥0.7、5分钟扫描、每小时报告。
    *   2026-03-17 已打包交付，包含完整文档 (README.md, INSTALL.md)。
*   **Documentation**: `regime_trader_ai_product/README.md`

## Upgrade Log for RegimeTrader AI
*   **Version**: v2.0-optimized
*   **Date**: 2026-03-21
*   **Description of Changes**:
    *   Multi-coin model training completed (5 symbols: BTC, ETH, BNB, SOL, XRP)
    *   Config updates: TRADING_SYMBOLS whitelist, RISK_PER_TRADE_PCT=5%, ADX=23
    *   Disabled macro risk module to avoid network dependencies
    *   Git commit pushed: 09189ba (excludes large .pkl files, includes metadata)
*   **Impact**: Enables multi-position capability; model ready for dry-run validation
*   **Related Task**: Phase 2 - Optimized bidirectional trading with multi-symbol model
