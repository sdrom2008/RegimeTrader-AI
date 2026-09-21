# Gate contrast — 2026-09-21 (CSV refreshed)

- Scope: offline 1y level backtest on whitelist **ETH/BNB/SOL/XRP** (BTC excluded).
- CSV last bar: **2026-09-21 07:00:00** (was stuck at 2026-09-10 06:00).
- Live paper gates unchanged: **35 / 0.80 / 15**.
- Elapsed: 3.8s

| Variant | Gated hits | Trades | WR | Agg PF | Sum PnL (4×$10k) |
|---|---:|---:|---:|---:|---:|
| `live_35_080_di15` (35/0.8/15) | 306 | 118 | 61.0% | 2.72 | $17,799 |
| `baseline_35_085_di15` (35/0.85/15) | 161 | 74 | 62.2% | 2.82 | $10,839 |
| `adx30_080_di15` (30/0.8/15) | 445 | 169 | 57.4% | 2.13 | $20,064 |
| `research_35_080_di12` (35/0.8/12) | 443 | 148 | 58.1% | 2.29 | $19,271 |

## Conclusion

1. **不推** live 门槛变更：ADX↓30 / |DI|↓12 交易量升但 PF 通常走弱；live 35/0.80/15 仍是平衡点。
2. 纸面长期空仓主因仍是 **ADX 熄火 + conf 未齐**，不是离线 edge 消失。
3. CSV 已续到今日，后续日报可直接对照本表。

