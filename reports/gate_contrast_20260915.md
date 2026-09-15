# Gate contrast — 2026-09-15 (|DI|≥15 aligned)

- Scope: offline `multi_full`, last **1y**, ETH/BNB/SOL/XRP, slip 2bps, level mode
- Diff vs 20260914: hard **|DI|≥15** (paper-identical) + ADX/conf + DI direction
- Purpose: conf 0.85 vs 0.80 (±ADX 30/35) under paper DI floor
- Runtime: 3.5s

| Variant | Gated hits | Trades | Agg PF | Sum PnL vs 10k×4 |
|---|---:|---:|---:|---:|
| `baseline_35_085_di15` (35/0.85/15) | 167 | 77 | 3.12 | $+12,700 |
| `adx30_085_di15` (30/0.85/15) | 239 | 107 | 2.56 | $+14,234 |
| `adx35_080_di15` (35/0.8/15) | 316 | 119 | 2.92 | $+19,726 |
| `adx30_080_di15` (30/0.8/15) | 460 | 172 | 2.25 | $+22,930 |

### baseline_35_085_di15

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 22 | 72.7 | 3.88 | +48.7 | 5.6 |
| BNB | 19 | 47.4 | 1.26 | +4.0 | 8.7 |
| SOL | 21 | 66.7 | 4.03 | +38.6 | 5.8 |
| XRP | 15 | 66.7 | 4.41 | +31.3 | 4.4 |

### adx30_085_di15

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 30 | 66.7 | 3.11 | +52.2 | 9.4 |
| BNB | 25 | 44.0 | 1.03 | -0.6 | 11.0 |
| SOL | 31 | 61.3 | 2.35 | +35.2 | 5.8 |
| XRP | 21 | 66.7 | 5.76 | +49.2 | 4.5 |

### adx35_080_di15

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

## Conclusion

1. **baseline 35/0.85/15:** hits=167 n=77 PF=3.12 sum=$+12,700
2. **ADX→30 keep 0.85/DI15:** hits=239 n=107 PF=2.56 (Δn +30)
3. **conf→0.80 keep ADX35/DI15:** hits=316 n=119 PF=2.92 (Δn +42)
4. **30/0.80/15:** hits=460 n=172 PF=2.25
5. |DI|≥15 cuts volume hard vs yesterday no-DI contrast (209→baseline here). Relative: conf 0.80 still preferred over ADX-only if unlocking paper.
6. Train overlap → relative only. **Live gates unchanged** (35/0.85/15). Document candidate conf→0.80 pending true WF OOS.
7. Paper journal 24h: 35/0.80/15 ≈4 ETH near-miss; 0.85 = 0.
