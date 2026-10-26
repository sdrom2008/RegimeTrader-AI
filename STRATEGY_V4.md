# STRATEGY_V4 — ETH direction sleeve

名称：**RegimeTrader-AI 方向袖**  
状态：纸交易只新开 ETH。慢速波动率袖和资金费套息见 `SLEEVES.md`，不在本执行器里开仓。

## 1. 标的

`TRADING_SYMBOLS = ['ETH/USDT']`。

模型文件仍是五币合训的 `regime_model_v2_multi_full.pkl`。BNB、SOL、XRP 留在训练集里，不留在纸面开仓名单里。已有非 ETH 纸仓只平不加。

## 2. 时间框架与扫描节奏

| 项 | 值 |
|----|-----|
| K 线周期 | **1h** |
| 预测窗口 | `LOOK_FORWARD_CANDLES=24`（约 24h） |
| 扫描间隔 | **`SCAN_INTERVAL=300` 秒（5 分钟）** |
| 最长持仓 | `MAX_HOLD_HOURS=24`（超时市价平） |
| 开仓 K 线 | 只用已收盘的 1h |

## 3. 信号规则

门槛冻结，不为了多攒样本再放宽。

1. 模型三分类：`Down(0) / Osc-HOLD(1) / Up(2)`，取预测类的概率。
2. ADX ≥ **35**，置信度 ≥ **0.80**，`|+DI − -DI| ≥ 15`。
3. 开多：`pred==2` 且 `+DI > -DI`。开空：`pred==0` 且 `-DI > +DI`。
4. 冷却 6 小时。同时最多 **1** 个仓。
5. 通过门槛后记入 `logs/signal_journal.jsonl`。`SIGNAL_OBSERVE_MODE=True` 时不开新仓。

ETH 对照（同一数据、同一出场）：模型 117 笔、盈亏比 1.74；裸 ADX/DI 规则 544 笔、盈亏比 1.15。见 `reports/eth_model_vs_rule.md`。

## 4. 风控与仓位

| 参数 | 值 |
|------|-----|
| 单仓风险 | `RISK_PER_TRADE_PCT=0.01`（1%） |
| 杠杆上限 | `LEVERAGE=2.0` |
| 止损 | `STOP_LOSS_ATR_MULT=1.5` × ATR |
| 止盈 | `TAKE_PROFIT_RR=2.5` |
| 移动止损 | `TRAIL_ACTIVATE_R=99`（关闭） |
| 单仓保证金上限 | `MAX_MARGIN_PCT_OF_EQUITY=0.40` |
| 最大同时持仓 | **1** |
| 冷却 | **6h** |
| 最长持仓 | **24h** |

仓位按权益 × 1% / |entry−SL| 计算，再受杠杆和保证金上限约束。

## 5. 滑点与手续费

- 手续费 4 bp，开仓和平仓都扣，按滑点后名义计。
- 不利滑点 2 bp。止盈、止损、超时平仓同样再滑一次。
- 资金费不进这本账。套息是另一条袖。

## 6. 开关

| 模式 | 配置 | 行为 |
|------|------|------|
| Observe | `SIGNAL_OBSERVE_MODE=True` | 扫描 + journal；不新开仓；已有仓位仍平仓 |
| Live paper（当前） | `SIGNAL_OBSERVE_MODE=False` | ETH 过门槛则按 1% 风险开纸仓 |

`live_executor.py` 在 `DRY_RUN=1` 下只记账，不向交易所发单。

## 7. 已知局限

- 方向袖的 walk-forward 每折重置资金，不是一条复利曲线。
- 没有资金费，止损按止损价加 2 bp 成交。
- 宏观过滤没有接上。
- 慢速袖和套息袖各自的报告不能直接加进这本权益。

## 8. 相关文件

- `config.py` — 方向袖参数
- `SLEEVES.md` — 三条袖为什么分开
- `paper_trader.py` — 纸面执行
- `slow_sleeve.py` / `carry_sleeve.py` — 另外两本账
- `reports/eth_model_vs_rule.md` — ETH 模型对规则
