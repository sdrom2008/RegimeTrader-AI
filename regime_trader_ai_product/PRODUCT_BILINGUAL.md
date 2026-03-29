# AI-Powered Regime Trading Engine / AI 模式识别量化交易引擎

## Executive Summary / 概述

The AI-Powered Regime Trading Engine is a sophisticated, automated trading system designed to navigate the complexities of the cryptocurrency markets. Its core innovation is an AI model that accurately identifies the prevailing market regime (Trend or Range) and dynamically adjusts its strategy, ensuring that trend-following logic is only applied in suitable market conditions. This AI-driven approach, combined with bi-directional trading capabilities and a multi-layered risk management framework, creates a robust and intelligent trading solution.

The project successfully evolved from a concept to a fully functional, backtestable trading engine, achieving a 94.25% accuracy in its regime predictions during testing.

AI 模式识别量化交易引擎是一个高度复杂的自动化交易系统，专门用于应对加密货币市场的复杂性。其核心创新在于使用 AI 模型准确识别当前市场状态（趋势或震荡），并动态调整策略，确保仅在合适的市场条件下应用趋势跟踪逻辑。这种 AI 驱动的方法，结合双向交易能力与多层风险管理框架，构建了一个稳健且智能的交易解决方案。

该项目已从概念发展为完全可回测的、功能完备的交易引擎，在测试中实现了 94.25% 的模式预测准确率。

## Core Features / 核心功能

*   **AI-Powered Regime Detection / AI 模式识别**：系统核心是一个训练好的 RandomForest 模型（`regime_model.pkl`），能够以高准确率预测市场处于“趋势”还是“震荡”状态。
*   **Dynamic Strategy Switching / 动态策略切换**：引擎仅在 AI 确认“趋势”模式时才激活趋势跟踪入场逻辑，有效过滤震荡市中不盈利的交易。
*   **Bi-Directional Trading / 双向交易**：系统能够执行多头（LONG）和空头（SHORT）头寸，从而从上涨和下跌趋势中均能获利。
*   **Multi-Layered Risk Management / 多层风险管理**：
    *   **宏观过滤**：实时分析新闻情绪，对逆势交易进行否决（例如在负面新闻时禁止开多）。
    *   **聪明钱监控**：分析 Binance 多空比数据，避免与大型知情资金对赌。
    *   **每笔风险控制**：使用 ATR 动态追踪止损，固定比例仓位模型（每笔交易风险不超过总资金 5%）。
*   **Automated & Scalable / 自动化与可扩展**：引擎设计为自主运行，扫描 Binance 前 60 个高流动性 USDT 交易对以发现机会，每5分钟自动运行一次，每小时发送汇总报告。

## System Architecture & Data Flow / 系统架构与数据流

1.  **数据获取**：从 Binance 获取实时 1 小时 K 线数据。
2.  **宏观过滤**：首先分析全球新闻情绪和聪明资金仓位，确立宏观偏多/偏空信号（如 `global_long_veto`）。
3.  **特征工程**：对每个交易对计算 16 个技术指标（与模型训练时完全一致）。
4.  **AI 模式预测**：将最新特征输入已加载的 AI 模型（`regime_model.pkl`），得到实时预测：`趋势 (1)` 或 `震荡 (0)`。
5.  **决策逻辑**：
    *   若预测为震荡，则跳过不操作。
    *   若预测为趋势，则进入下一步。
6.  **入场逻辑**：第二层基于规则的 `MarketStateAnalyzer` 判断具体趋势方向（上升/下降）以触发多头或空头交易，同时受宏观否决条件约束。
7.  **持仓管理**：系统使用移动止损并跟踪总体盈亏。

## Key Components & Technologies / 关键组件与技术栈

*   **核心引擎**：`paper_trader.py` - 集成所有功能的主执行脚本。
*   **AI 模型**：`regime_model.pkl` - 序列化保存的 scikit-learn 模型文件。
*   **数据管道**：
    *   `fetch_historical_data.py`：下载历史数据用于训练。
    *   `generate_features.py`：对原始数据进行特征工程。
    *   `train_regime_model.py`：标注数据并训练 AI 模型。
*   **依赖**：`requirements.txt` - 所有必要的 Python 库。
*   **技术栈**：
    *   **语言**：Python 3.12
    *   **库**：`pandas`, `ccxt`, `scikit-learn`, `pandas_ta`, `numpy`

## The AI Brain: Model Details / AI 大脑：模型详情

*   **算法**：scikit-learn 的 `RandomForestClassifier`（100 棵树，类别权重平衡）。
*   **训练数据**：2 年 BTC/USDT 1 小时数据（19,129 个样本，16 个特征）。
*   **标注策略**：前望法，将未来 24 小时价格波动超过当前 ATR 3 倍定义为“趋势”。类别分布：趋势 84.5%，震荡 15.5%。
*   **性能**（测试集 3,826 样本）：
    *   **总体准确率**：**94.25%**
    *   **趋势召回率**：**99%**（几乎不遗漏真实趋势）
    *   **趋势精确率**：**94%**（每 20 个趋势信号约有 1 个误报）
    *   **震荡召回率**：**66%**（不需要完美，系统在震荡市本就不开仓）
*   **意义**：模型高度优化以捕捉趋势（高召回），完全符合趋势跟踪策略需求。震荡误判由 `MarketStateAnalyzer` 与宏观否决进行二次过滤来缓解。

## Current Deployment Status / 当前部署状态

*   **模拟交易**：每5分钟运行 `live_executor.py`（DRY_RUN=1），执行扫描与交易。
*   **初始资金**：10,000 USDT（3 倍杠杆）。
*   **报告**：
    *   每小时整点：执行器发送资产、持仓、盈亏摘要（WhatsApp）
    *   每小时第5分钟：绩效分析器发送详细绩效统计（胜率、盈亏比、回撤等）
*   **通知**：扫描摘要与交易信号实时发送至 WhatsApp。
*   **性能追踪**：所有交易历史与状态持久化至 `paper_trade_state.json`。
*   **定时任务**：
    *   `*/5 * * * * .../live_executor.py`（扫描与交易）
    *   `5 * * * * .../performance_analyzer.py`（绩效分析）
    *   `*/10 * * * * .../live_multi_hedge_engine.py`（配对策略）

## Getting Started / Deployment / 快速开始 / 部署

1.  **环境配置**：创建 Python 虚拟环境，使用 `pip install -r requirements.txt` 安装所有依赖。
2.  **配置**：如需使用基于 LLM 的情绪分析，将必要的 API 密钥（如 `GEMINI_API_KEY`）放入 `.env` 文件。
3.  **运行**：执行 `python paper_trader.py` 启动引擎。系统将执行一次扫描与持仓管理。要持续运行，请通过 cron 或类似任务调度器设置周期性执行。
4.  **报告**：每小时报告脚本 `paper_trader_report.py` 会自动运行并发送消息。
5.  **通知**：确保 OpenClaw 的 WhatsApp 通道已正确配置。

## Important Notes / 重要提示

*   模型在 BTC 1h 数据上训练，直接用于其他币种可能存在分布差异。建议在实盘前进行充分的跨品种回测。
*   当前宏观过滤使用 Stub（中性情绪），生产环境可接入真实新闻 LLM 或情绪 API。
*   滑点与流动性：仅扫描前 40 个高流动性 USDT 交易对，以减少滑点影响。
*   风险提示：本软件仅供研究学习，使用实盘需自行承担风险。
