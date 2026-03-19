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
# 将训练好的模型放置为 regime_model.pkl
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

## 📈 监控与报告

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

- 执行器日志：`logs/live_executor_cron_dry.log`
- 绩效分析日志：`logs/performance_analyzer.log`
- 绩效报告文件：`logs/performance/performance_YYYYMMDD_HHMM.md`
- 配对策略日志：`logs/2026-03-17_multi_hedge.log`

---

## 🔧 常见问题

### Q：模拟盘和实盘逻辑一致吗？
A：完全一致。模拟盘使用 `paper_trader.py` 的本地资金管理，实盘直接调用Binance API，但仓位计算、止损、风险检查公式相同。

### Q：如何调整扫描频率？
A：修改 crontab 的 `*/5 * * * *` 为其他间隔（注意API限速）。

### Q：止损是市价单还是限价单？
A：模拟和实盘均使用 `STOP_MARKET` 订单，触发后以市价平仓，可能出现滑点。

### Q：最大回撤控制？
A：单笔亏损固定（5%），但未设整体回撤止损。建议实盘前增加每日最大亏损限制。

---

## 📁 项目结构

```
regime_trader_ai_product/
├── code/                    # 核心策略模块
│   ├── market_state_logic.py
│   ├── sentiment_handler.py
│   └── ...
├── config/                  # 配置文件
│   └── .env.example
├── data/                   # 历史数据缓存
├── logs/                   # 运行日志
├── live_executor.py       # 主执行器（实盘/模拟入口）
├── paper_trader.py        # 模拟盘引擎
├── paper_trade_state.json # 模拟盘状态（自动生成）
├── regime_model.pkl       # AI模型
├── requirements.txt       # 依赖列表
├── train_regime_model.py  # 模型训练脚本
├── PRD_draft.md           # 产品需求文档
└── PRODUCT_BILINGUAL.md   # 产品双语介绍
```

---

## 📝 更新日志

### v1.0 (2026-03-17)
- 首次打包发布
- 模拟/实盘逻辑对齐
- 增强报告（持仓详情、盈亏）
- 风险控制完整实现
- 每5分钟扫描，每小时报告

---

## ⚠️ 风险提示

- 本软件为实验性质，**不保证盈利**
- 实盘前务必充分测试
- 建议从小资金开始，逐步放大
- 市场有风险，决策需谨慎

---

**开发者：** 虾子 (OpenClaw Agent)  
**版本：** 1.0  
**最后更新：** 2026-03-17
