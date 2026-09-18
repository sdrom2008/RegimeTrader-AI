# Gate contrast — 2026-09-18 (|DI| hard floor)

- Scope: offline `multi_full`, last **1y**, ETH/BNB/SOL/XRP, slip 2bps, level mode
- Live paper: **35 / 0.80 / 15**（今日未改门槛）
- Runtime: 4.0s
- Note: 纸面近 36h 有一次 ~5.0h wall-clock jump（已由 sleep 心跳检出并自愈）；主矛盾仍是 ADX 熄火。

| Variant | Gated hits | Trades | Agg PF | Sum PnL vs 10k×4 |
|---|---:|---:|---:|---:|
| `baseline_35_085_di15` (35/0.85/15) | 167 | 77 | 3.12 | $12,700 |
| `live_35_080_di15` (35/0.8/15) | 316 | 119 | 2.92 | $19,726 |
| `adx30_080_di15` (30/0.8/15) | 460 | 172 | 2.25 | $22,930 |
| `research_35_080_di12` (35/0.8/12) | 456 | 147 | 2.39 | $20,407 |

### baseline_35_085_di15

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 22 | 72.7 | 3.88 | +48.7 | 5.6 |
| BNB | 19 | 47.4 | 1.26 | +4.0 | 8.7 |
| SOL | 21 | 66.7 | 4.03 | +38.6 | 5.8 |
| XRP | 15 | 66.7 | 4.41 | +31.3 | 4.4 |

### live_35_080_di15

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 30 | 73.3 | 4.77 | +75.1 | 5.8 |
| BNB | 28 | 50.0 | 1.20 | +4.0 | 8.1 |
| SOL | 38 | 57.9 | 2.42 | +52.6 | 6.8 |
| XRP | 23 | 69.6 | 4.88 | +58.0 | 4.4 |

### adx30_080_di15

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 42 | 57.1 | 2.21 | +49.9 | 11.6 |
| BNB | 41 | 56.1 | 1.69 | +25.1 | 9.4 |
| SOL | 51 | 56.9 | 2.00 | +57.3 | 7.8 |
| XRP | 38 | 63.2 | 3.26 | +85.4 | 6.7 |

### research_35_080_di12

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 36 | 63.9 | 2.83 | +60.8 | 6.3 |
| BNB | 33 | 51.5 | 1.27 | +6.9 | 10.8 |
| SOL | 50 | 54.0 | 1.99 | +54.0 | 10.6 |
| XRP | 28 | 67.9 | 4.30 | +72.8 | 4.8 |

## Conclusion

1. Live **35/0.80/15** 数字与 9/16–9/17 一致（数据 CSV mtime 未变）→ PF≈2.92 / 119 trades。
2. **不推** DI→12 / ADX→30 上 live（PF 掉）。
3. Train overlap → 仅相对对照。
4. Journal 近 24h：ordered choke 几乎全是 fail_adx；ETH 曾近失 ADX≈34.7。
