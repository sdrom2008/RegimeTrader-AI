# Gate contrast — 2026-09-19 (|DI| hard floor)

- Scope: **no new offline backtest** — `data/*_1h_6y.csv` last bar still **2026-09-10 06:00** (unchanged vs 9/18).
- Live paper: **35 / 0.80 / 15**（今日未改门槛）
- Paper executor was **DEAD ~21.5h** at analysis time; journal ends 2026-09-18T09:34Z.

Numbers identical to `gate_contrast_20260918.md`:

| Variant | Gated hits | Trades | Agg PF | Sum PnL vs 10k×4 |
|---|---:|---:|---:|---:|
| `baseline_35_085_di15` (35/0.85/15) | 167 | 77 | 3.12 | $12,700 |
| `live_35_080_di15` (35/0.8/15) | 316 | 119 | 2.92 | $19,726 |
| `adx30_080_di15` (30/0.8/15) | 460 | 172 | 2.25 | $22,930 |
| `research_35_080_di12` (35/0.8/12) | 456 | 147 | 2.39 | $20,407 |

## Journal choke (ref last HB)

- 24h uniq: fail_adx=83 / fail_conf=1 / PASS=0
- 72h uniq: fail_adx=140 / fail_conf=52 / fail_di=20 / PASS=0

## Conclusion

1. **不推** live 门槛变更。
2. 今日优先工程：恢复 DRY_RUN 常驻 + heartbeat 健康检查（已做）。
3. 下一步研究刀：刷新 CSV 后再重跑 1y gate contrast。
