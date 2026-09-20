# Gate contrast — 2026-09-20 (|DI| hard floor)

- Scope: **no new offline backtest** — `data/*_1h_6y.csv` last bar still **2026-09-10 06:00** (unchanged vs 9/18–9/19).
- Live paper: **35 / 0.80 / 15**（今日未改门槛）
- Paper executor: ~3.7h **host pause** (wall-clock jump)；唤醒后 status=ok；equity $11046.63 空仓。

Numbers identical to `gate_contrast_20260918.md`:

| Variant | Gated hits | Trades | Agg PF | Sum PnL vs 10k×4 |
|---|---:|---:|---:|---:|
| `baseline_35_085_di15` (35/0.85/15) | 167 | 77 | 3.12 | $12,700 |
| `live_35_080_di15` (35/0.8/15) | 316 | 119 | 2.92 | $19,726 |
| `adx30_080_di15` (30/0.8/15) | 460 | 172 | 2.25 | $22,930 |
| `research_35_080_di12` (35/0.8/12) | 456 | 147 | 2.39 | $20,407 |

## Journal choke (analysis time)

- 24h uniq: fail_adx=87 / fail_conf=1 / PASS=0
- 72h uniq: fail_adx=178 / fail_conf=2 / PASS=0
- Post-pause near-miss: SOL ADX 45.7 / conf 0.68 / |DI| 14.6

## Conclusion

1. **不推** live 门槛变更。
2. 今日优先工程：stale-HB watchdog + 平仓早落盘 + pause 追扫（已做）。
3. 下一步研究刀：刷新 CSV 后再重跑 1y gate contrast。
