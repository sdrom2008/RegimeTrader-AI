# Gate contrast — 2026-09-24 (CSV refreshed)

- Scope: offline 1y level backtest on whitelist **ETH/BNB/SOL/XRP** (BTC excluded).
- CSV last bar: **2026-09-24 07:00:00** (was 2026-09-21 07:00).
- Live paper gates unchanged: **35 / 0.80 / 15**.
- Elapsed: 3.4s

| Variant | Gated hits | Trades | WR | Agg PF | Sum PnL (4×$10k) |
|---|---:|---:|---:|---:|---:|
| `live_35_080_di15` (35/0.8/15) | 305 | 117 | 62.4% | 2.84 | $18,442 |
| `baseline_35_085_di15` (35/0.85/15) | 160 | 74 | 63.5% | 2.95 | $11,200 |
| `adx30_080_di15` (30/0.8/15) | 444 | 168 | 57.7% | 2.16 | $20,306 |
| `research_35_080_di12` (35/0.8/12) | 442 | 147 | 59.2% | 2.37 | $19,957 |

## Conclusion

1. **不推** live 门槛变更：ADX↓30 / |DI|↓12 抬量但 PF 走弱；live 35/0.80/15 仍是平衡点。
2. 纸面长期空仓主因仍是 **ADX 熄火**（今日 near max_adx≈31.6 < 35），不是离线 edge 消失。
3. CSV 已续到今日；9/22–9/23 宿主长 pause 导致日报空窗，工程侧补 watchdog 可观测性。
