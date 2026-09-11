# STRATEGY_V4 — Observe-Ready

名称：**RegimeTrader-AI STRATEGY_V4（observe-ready）**  
状态：纸交易开仓中（`SIGNAL_OBSERVE_MODE=False`）；journal 仍持续写入，可翻 True 仅观察。

## 1. 标的宇宙（Universe）

锁定训练集五币（与 `regime_model_v2_multi_full.pkl` 一致）：

- `BTC/USDT`
- `ETH/USDT`
- `BNB/USDT`
- `SOL/USDT`
- `XRP/USDT`

配置：`TRADING_SYMBOLS`（非空时不扫全市场 top-N）。

## 2. 时间框架与扫描节奏

| 项 | 值 |
|----|-----|
| K 线周期 | **1h** |
| 预测窗口 | `LOOK_FORWARD_CANDLES=24`（约 24h） |
| 扫描间隔 | **`SCAN_INTERVAL=300` 秒（5 分钟）** |
| 最长持仓 | `MAX_HOLD_HOURS=24`（超时市价平） |

## 3. 信号规则

1. 模型三分类：`Down(0) / Osc-HOLD(1) / Up(2)`，取 `predict_proba` 最大类置信度。
2. **硬门槛**
   - `ADX >= ADX_STRONG_THRESHOLD`（**25**）
   - `confidence >= CONFIDENCE_THRESHOLD`（**0.80**）
3. **DI 方向过滤（保留）**
   - 开多（BUY）：`pred==2` 且 `+DI > -DI`
   - 开空（SELL）：`pred==0` 且 `-DI > +DI`
4. 通过门槛后记入 `logs/signal_journal.jsonl`；观察模式下**不新开仓**。
5. 冷却：平仓后同币种 `COOLDOWN_HOURS=6`（`MIN_BARS_BETWEEN_TRADES=6`）。
6. 组合：`MAX_CONCURRENT_POSITIONS=2`。

## 4. 风控与仓位

| 参数 | 值 |
|------|-----|
| 单仓风险 | `RISK_PER_TRADE_PCT=0.02`（2%） |
| 杠杆上限 | `LEVERAGE=2.0` |
| 止损 | `STOP_LOSS_ATR_MULT=1.5` × ATR |
| 止盈 | `TAKE_PROFIT_RR=2.5`（相对止损距离） |
| 移动止损 | `TRAILING_STOP_ATR=1.5` × ATR；`TRAIL_ACTIVATE_R=1.0`（浮盈≥1R 才 trail，SL 抬到至少保本） |
| 单仓保证金上限 | `MAX_MARGIN_PCT_OF_EQUITY=0.40` |
| 最大同时持仓 | **2** |
| 冷却 | **6h** |
| 最长持仓 | **24h** |

仓位按权益 × 风险 / |entry−SL| 计算，并受杠杆名义上限约束。

## 5. 滑点与手续费假设

- **手续费**：`fee_rate=0.0004`（4 bps），按**滑点后名义**计。
- **滑点**：`SLIPPAGE_BPS=2.0`（每笔成交不利方向）；`SLIPPAGE_ATR_FRAC=0.0`（关闭，可按需开启）。
- 规则（仅不利）：
  - 开多 / 平空（买）：`price × (1 + bps/10000)`
  - 开空 / 平多（卖）：`price × (1 − bps/10000)`
  - TP / SL / MAX_HOLD 触发价同样再滑不利方向后再算 PnL。
- 纸交易与离线回测（`paper_trader.py` / `backtest_v2_offline.py`）共用同一套逻辑。

## 6. Observe vs Live Paper 开关

| 模式 | 配置 | 行为 |
|------|------|------|
| **Observe** | `SIGNAL_OBSERVE_MODE=True` | 扫描 + journal；**不新开仓**；已有仓位仍平仓 |
| **Live paper（当前）** | `SIGNAL_OBSERVE_MODE=False` | 过门槛即按风控开纸仓 |

用户当前在收集信号准确率；策略包已 ready，准确率达标后翻 False 即可。

## 7. 已知局限

- 离线回测非严格 walk-forward：训练数据与回测区间可能重叠，分类准确率偏乐观。
- 回测按币种独立账户（各 $10k），无法完整复现纸交易共享保证金与 `max_pos=1` 跨币约束。
- 执行假设简化：1h 收盘入场 + HL 触发再滑点；无 funding、无深度/冲击成本。
- 宏观/新闻风控当前禁用。
- 历史同配置（甚至更松门槛）离线权益曲线仍大幅回撤；**observe 优先验证方向准确率**，勿直接放大实盘。
- 滑点 2bps 为保守纸面假设，实盘流动性差时实际成本可能更高。

## 8. 相关文件

- `config.py` — STRATEGY_V4 参数与 `SLIPPAGE_*`
- `STRATEGY_V4.md` — 本文档
- `paper_trader.py` — `apply_slippage` + observe/live 执行
- `backtest_v2_offline.py` — 同滑点回测；`--compare-slippage` 写对比报告
- `reports/backtest_slippage_v4.md` — 有/无滑点对比
