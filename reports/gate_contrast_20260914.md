# Gate contrast — 2026-09-14

- Scope: offline `backtest_v2_offline` level mode, last **1y**, symbols ETH/BNB/SOL/XRP, slip 2bps
- Note: offline backtest uses ADX+conf + DI direction (not |DI|≥15 hard floor); paper also requires |DI|≥15
- Purpose: check whether ADX 30 alone unlocks edge vs conf 0.80

| Variant | Trades | Agg PF (gross win/loss) | Sum symbol PnL vs 10k |
|---|---:|---:|---:|
| `baseline_35_085` (35/0.85) | 209 | 1.84 | $+19854 |
| `adx30_085` (30/0.85) | 326 | 1.61 | $+23472 |
| `adx35_080` (35/0.8) | 270 | 1.77 | $+25356 |
| `adx30_080` (30/0.8) | 407 | 1.62 | $+32292 |

## Per-symbol detail

### baseline_35_085 (ADX≥35, conf≥0.85)

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 48 | 64.6 | 2.98 | +104.9 | 7.9 |
| BNB | 43 | 48.8 | 1.40 | +16.1 | 11.8 |
| SOL | 67 | 47.8 | 1.61 | +46.5 | 18.7 |
| XRP | 51 | 45.1 | 1.49 | +31.0 | 15.3 |

### adx30_085 (ADX≥30, conf≥0.85)

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 82 | 54.9 | 2.03 | +95.5 | 11.8 |
| BNB | 58 | 44.8 | 1.36 | +20.9 | 14.1 |
| SOL | 104 | 45.2 | 1.38 | +47.0 | 15.1 |
| XRP | 82 | 48.8 | 1.68 | +71.3 | 14.7 |

### adx35_080 (ADX≥35, conf≥0.8)

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 67 | 55.2 | 2.17 | +93.3 | 7.9 |
| BNB | 55 | 47.3 | 1.33 | +16.7 | 15.6 |
| SOL | 82 | 46.3 | 1.44 | +44.9 | 15.0 |
| XRP | 66 | 53.0 | 2.08 | +98.6 | 13.6 |

### adx30_080 (ADX≥30, conf≥0.8)

| Symbol | Trades | WR% | PF | Ret% | MaxDD% |
|---|---:|---:|---:|---:|---:|
| ETH | 104 | 48.1 | 1.64 | +74.9 | 13.4 |
| BNB | 77 | 50.6 | 1.78 | +64.6 | 13.0 |
| SOL | 124 | 42.7 | 1.22 | +30.6 | 18.5 |
| XRP | 102 | 52.9 | 1.92 | +152.8 | 15.7 |

## Conclusion

1. **ADX 30 alone (keep conf 0.85):** trades 209→326, agg PF **1.84→1.61** — volume up, edge diluted.
2. **conf 0.80 (keep ADX 35):** trades 209→270, agg PF **1.84→1.77** — better PF retention than ADX-only loosen.
3. **Both loose (30/0.80):** max sum PnL but PF 1.62; paper journal still needs conf≤0.80 to unlock *current* regime.
4. **Do not change live gates today.** Next research: walk-forward with paper-identical |DI|≥15 on conf=0.80 (±ADX30).
5. Runtime: 3.2s

