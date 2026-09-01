License: MIT
# RegimeTrader AI - 智能趋势跟踪量化交易系统

> AI驱动的期货自动交易，基于机器学习识别市场状态，捕捉高胜率趋势机会。

---

## 🚀 快速开始

### 环境要求
- Python 3.12+
- Binance 期货账户 + API Key
- OpenClaw CLI（用于 WhatsApp 通知）

### 安装步骤

1. 克隆项目并进入目录：
```bash
cd regime_trader_ai_product/
```

2. 创建虚拟环境并安装依赖：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
# 创建 .env 文件（从示例复制）
cp config/.env.example .env
# 编辑 .env，填入你的 Binance API Key/Secret
```

4. 准备 AI 模型：
```bash
# v2 模型（推荐）：多币种三分类
# 下载 regime_model_v2_multi_full.pkl 到项目根目录
# 已在项目根目录创建符号链接
```

5. 初始化模拟状态：
```bash
# 首次运行自动创建 paper_trade_state.json
python paper_trader.py
```

---

## ⚙️ 配置说明

### 核心参数（`paper_trader.py` 顶部）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `LEVERAGE` | 3.0 | 交易杠杆倍数 |
| `INITIAL_BALANCE` | 10000.0 | 模拟盘初始资金 |
| `RISK_PER_TRADE_PCT` | 0.05 | 单笔交易风险（总资产百分比）|
| `SCAN_INTERVAL` | 300 | 扫描间隔（秒）|
| `SCAN_LIMIT` | 60 | 扫描前 N 个交易对 |
| `MARKET_CONF_THRESHOLD` | 0.7 | MarketStateAnalyzer 置信度阈值 |

### 环境变量（`.env`）

```ini
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

---

## 🏃 运行模式

### 模拟盘（Dry Run）
```bash
DRY_RUN=1 python -m regime_trader_ai_product.live_executor
```
- 使用本地 `paper_trade_state.json` 管理资金
- 不发起真实订单
- 发送 WhatsApp 报告（仅在整点）

### 实盘（Live）
```bash
DRY_RUN=0 python -m regime_trader_ai_product.live_executor
```
- 连接 Binance 期货 API
- 自动下单、设止损
- **务必先小资金测试**

---

## 📊 策略逻辑

### 1. 信号生成流程

```
扫描前60个USDT交易对
  ↓
对每个交易对：
  - 拉取1小时K线（250根）
  - 计算技术指标（ADX、布林带、ATR、RSI、EMA）
  - AI模型预测市场状态：RANGE vs TREND
  - 若为TREND，调用 MarketStateAnalyzer 确定方向与置信度
  - 宏观过滤：恐惧贪婪指数 + 多空持仓比
  - 仓位计算：风险5% → 名义金额 → 保证金
  - 可用保证金检查 → 开仓
```

### 2. 风险控制

- **止损**：ATR × 1.5，动态移动止损
- **仓位**：单笔风险固定为总资产 5%
- **杠杆**：3 倍
- **分散**：最多同时 3 个品种（资金自然限制）

### 3. 资金模型

**模拟盘：**
- `balance`：现金余额
- 开仓：`balance -= margin`
- 平仓：`balance += margin + pnl - fee`
- 总资产 = `balance` + Σ未实现盈亏

**实盘：**
- 直接读取交易所 `USDT` 余额
- 开平仓由交易所自动处理
- 代码只读余额计算可用资金

---

## 📊 模型

### v2 (当前版本)
- **训练日期**：2026-03-24
- **数据**：5币种6年1h数据（BTC, ETH, BNB, SOL, XRP）
- **样本数**：259,120
- **类型**：三分类（SELL/HOLD/BUY）
- **准确率**：86%（验证集）
- **文件**：`regime_model_v2_multi_full.pkl`
- **参数**：
  - ADX 阈值：20
  - 置信度阈值：0.55
  - 扫描范围：前60个流动性币种
- **注意**：需配合 `config.py` 使用 v2 配置

---

## 📈 性能追踪

### 自动报告（每小时整点）

#### 1. 执行器报告（live_executor）
通过 WhatsApp 发送：
- 总资产、现金余额
- 持仓详情（数量、开仓价、当前价、未实现盈亏、止损价）
- 本小时新开/平仓记录
- 手续费汇总

#### 2. 绩效分析报告（performance_analyzer）
每小时第5分钟生成并发送绩效摘要，包含：
- 总收益率、胜率、盈亏比
- 已实现盈亏、未实现盈亏
- 当前持仓数量
完整 Markdown 报告保存至 `logs/performance/`

### 日志位置

- **v2 执行器日志**：`logs/v2_live_*.log`
- **v2 训练日志**：`logs/train_v2_*.log`
- **绩效分析日志**：`logs/performance_analyzer.log`
- **绩效报告文件**：`logs/performance/performance_YYYYMMDD_HHMM.md`

---

## 🔧 常见问题

### Q：模拟盘和实盘逻辑一致吗？
A：完全一致。模拟盘使用 `paper_trader.py` 的本地资金管理，实盘直接调用Binance API，但仓位计算、止损、风险检查公式相同。

### Q：如何调整扫描频率？
A：修改 `config.py` 中的 `SCAN_INTERVAL`（秒），或使用 `live_executor.py` 的循环间隔。

### Q：止损是市价单还是限价单？
A：模拟和实盘均使用 `STOP_MARKET` 订单，触发后以市价平仓，可能出现滑点。

### Q：最大回撤控制？
A：单笔亏损固定（5%），但未设整体回撤止损。建议实盘前增加每日最大亏损限制。

---

## 📁 项目结构

```
regime_trader_ai_product/
├── code/                          # 核心策略模块
│   ├── market_state_logic.py
│   ├── sentiment_handler.py
│   └── ...
├── config/                        # 配置文件
│   └── .env.example
├── data/                         # 历史数据缓存
├── logs/                         # 运行日志
├── live_executor.py             # 主执行器（实盘/模拟入口）
├── paper_trader.py              # 模拟盘引擎（v2）
├── paper_trade_state_v2.json    # 模拟盘状态（v2，自动生成）
├── regime_model_v2_multi_full.pkl   # v2 AI 模型（多币种）
├── regime_model_v2_multi_full_meta.json  # v2 模型元数据
├── config.py                    # v2 配置（扫描参数、阈值）
├── strategy_v2_quantile.py      # v2 特征工程与标签
├── train_model_v2_multi.py      # v2 多币种训练脚本
├── requirements.txt             # 依赖列表
├── PRD_draft.md                 # 产品需求文档
└── PRODUCT_BILINGUAL.md         # 产品双语介绍
```

---

## 📝 更新日志

### v2.1 (2026-03-24)
- ✅ 修复标签泄漏 bug（`strategy_v2_quantile.py`）
- ✅ 放宽交易参数：全市场扫描 + ADX 20 + 置信度 0.55
- ✅ 重新训练模型（5币种6年数据，259k样本）
- ✅ 产生首个新交易（NEAR/USDT 做空）
- 📝 文档更新（模型版本、项目结构）

### v2.0 (2026-03-20)
- 升级三分类模型（SELL/HOLD/BUY）
- 多币种联合训练（BTC/ETH/BNB/SOL/XRP）
- 动态分位数阈值标签
- 新配置系统（`config.py`）
- 方向特征工程（DI_diff, +DI_cross 等）

---

## ⚠️ 风险提示

- 本软件为实验性质，**不保证盈利**
- 实盘前务必充分测试
- 建议从小资金开始，逐步放大
- 市场有风险，决策需谨慎

---

**开发者：** 虾子 (OpenClaw Agent)  
**版本：** 2.1  
**最后更新：** 2026-03-24
