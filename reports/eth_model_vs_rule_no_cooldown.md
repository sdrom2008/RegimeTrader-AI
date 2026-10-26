# ETH walk-forward: cooldown 6h vs 0h

- Generated (UTC): 2026-10-26 15:50
- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.
- Paired sim: one RandomForest fit per fold (`n_jobs=1`, seed 42), then `simulate_fold(..., cooldown_bars=6)` vs `cooldown_bars=0`.
- Gates / exits: ADX≥35, conf≥0.80, |DI|≥15, SL 1.5×ATR, TP 2.5R, trail@99R, max hold 24h, fee 4bps×2, slip 2bps.
- **Research sets cooldown_off=0.** Paper / live default remains `MIN_BARS_BETWEEN_TRADES=6` / `COOLDOWN_HOURS=6` (config.py untouched).
- This-run OOS: **2021-10-20 → 2026-09-24** = 1800 days ≈ 4.9281 years.
- Runtime: 28s

## Aggregate contrast (paired, this environment)

| Arm | Cooldown | Trades | WR | PF | Ann. trades | Sum PnL |
|-----|----------|--------|----|----|-------------|---------|
| Model | 6h | 80 | 43.8% | 1.29 | 16.2 | $1,235 |
| Model | 0h | 87 | 44.8% | 1.24 | 17.7 | $1,072 |
| Rule | 6h | 668 | 37.1% | 1.05 | 135.5 | $1,819 |
| Rule | 0h | 849 | 38.6% | 1.10 | 172.3 | $5,242 |

Ann. trades = total trades / (1800/365.25).

## Exit reasons (paired)

- Model 6h: EOD 1, MAX_HOLD 23, SL/TRAIL 39, TP 17
- Model 0h: EOD 1, MAX_HOLD 27, SL/TRAIL 42, TP 17
- Rule 6h: EOD 5, MAX_HOLD 154, SL/TRAIL 371, TP 138
- Rule 0h: EOD 4, MAX_HOLD 196, SL/TRAIL 463, TP 186

## Published 6h baseline (historical cite)

From `reports/eth_model_vs_rule.md` (UTC 2026-10-26 03:26), OOS 2021-10-27→2026-10-01 = 1800d ≈ 4.9281y. Fold calendar differs under the current feature pipeline on this box, so these are **not** re-simulated here; cited for Boss's ~1.7 PF reference.

| Arm | Cooldown | Trades | WR | PF | Ann. trades | Sum PnL |
|-----|----------|--------|----|----|-------------|---------|
| Model | 6h | 117 | 48.7% | 1.74 | 23.7 | $8,266 |
| Rule | 6h | 544 | 40.4% | 1.15 | 110.4 | $9,362 |

## Per fold (M/R at 6h, then M/R at 0h)

| Fold | Test | M6 n | M6 PF | M6 ret | R6 n | R6 PF | R6 ret | M0 n | M0 PF | M0 ret | R0 n | R0 PF | R0 ret |
|------|------|------|-------|--------|------|-------|--------|------|-------|--------|------|-------|--------|
| 0 | 2021-10-20→2022-01-18 | 0 | 0.00 | +0.0% | 32 | 1.06 | +0.5% | 0 | 0.00 | +0.0% | 35 | 1.27 | +4.7% |
| 1 | 2022-01-18→2022-04-18 | 2 | 0.03 | -1.0% | 30 | 0.72 | -6.1% | 3 | 0.02 | -2.1% | 35 | 0.71 | -7.5% |
| 2 | 2022-04-18→2022-07-17 | 1 | 0.00 | -1.0% | 28 | 2.05 | +13.2% | 1 | 0.00 | -1.0% | 32 | 1.59 | +9.2% |
| 3 | 2022-07-17→2022-10-15 | 2 | inf | +3.4% | 31 | 1.61 | +8.8% | 2 | inf | +3.4% | 39 | 1.43 | +7.9% |
| 4 | 2022-10-15→2023-01-13 | 3 | 2.17 | +1.1% | 26 | 0.63 | -6.9% | 3 | 2.17 | +1.1% | 35 | 0.72 | -7.1% |
| 5 | 2023-01-13→2023-04-13 | 6 | 3.49 | +5.3% | 36 | 0.57 | -13.0% | 6 | 3.49 | +5.3% | 49 | 0.55 | -17.3% |
| 6 | 2023-04-13→2023-07-12 | 1 | inf | +0.5% | 28 | 0.69 | -7.4% | 1 | inf | +0.5% | 37 | 0.82 | -5.9% |
| 7 | 2023-07-12→2023-10-10 | 2 | 0.46 | -0.7% | 37 | 1.11 | +0.2% | 2 | 0.46 | -0.7% | 49 | 1.25 | +4.4% |
| 8 | 2023-10-10→2024-01-08 | 2 | 0.32 | -0.8% | 40 | 0.37 | -17.8% | 3 | 0.16 | -1.9% | 53 | 0.87 | -6.1% |
| 9 | 2024-01-08→2024-04-07 | 0 | 0.00 | +0.0% | 41 | 1.43 | +9.3% | 0 | 0.00 | +0.0% | 51 | 1.36 | +9.0% |
| 10 | 2024-04-07→2024-07-06 | 4 | 0.75 | -1.0% | 43 | 0.64 | -10.8% | 4 | 0.75 | -1.0% | 58 | 0.93 | -4.3% |
| 11 | 2024-07-06→2024-10-04 | 5 | 0.58 | -1.9% | 35 | 0.75 | -6.7% | 6 | 0.78 | -1.1% | 45 | 0.76 | -8.6% |
| 12 | 2024-10-04→2025-01-02 | 6 | 3.22 | +4.9% | 33 | 1.48 | +8.7% | 6 | 3.22 | +4.9% | 39 | 1.52 | +10.4% |
| 13 | 2025-01-02→2025-04-02 | 9 | 0.02 | -7.3% | 35 | 0.43 | -14.7% | 11 | 0.02 | -8.3% | 46 | 0.66 | -11.1% |
| 14 | 2025-04-02→2025-07-01 | 0 | 0.00 | +0.0% | 34 | 1.50 | +8.2% | 0 | 0.00 | +0.0% | 46 | 1.32 | +7.5% |
| 15 | 2025-07-01→2025-09-29 | 7 | 2.06 | +2.4% | 39 | 1.62 | +10.7% | 7 | 2.06 | +2.4% | 46 | 1.54 | +11.0% |
| 16 | 2025-09-29→2025-12-28 | 4 | 0.70 | -0.7% | 26 | 0.79 | -4.4% | 4 | 0.70 | -0.7% | 34 | 0.64 | -9.3% |
| 17 | 2025-12-28→2026-03-28 | 5 | inf | +7.2% | 35 | 1.83 | +14.0% | 6 | inf | +7.4% | 44 | 2.47 | +28.6% |
| 18 | 2026-03-28→2026-06-26 | 9 | 1.13 | +0.5% | 30 | 2.01 | +15.5% | 9 | 1.42 | +1.9% | 41 | 1.60 | +13.0% |
| 19 | 2026-06-26→2026-09-24 | 12 | 0.89 | -1.2% | 29 | 0.84 | -3.8% | 13 | 0.76 | -2.3% | 35 | 0.94 | -2.4% |

## Read this

- Model: cooldown off lifts trades 80 → 87 but PF 1.29 → 1.24 and Sum PnL $1,235 → $1,072.
- Rule: trades 668 → 849; PF 1.05 → 1.10; Sum PnL $1,819 → $5,242.
- Repro: `python eth_cooldown_compare.py` or `python eth_model_vs_rule.py --cooldown 0 --out reports/eth_model_vs_rule_no_cooldown.md` (single-arm only).
- Paper default cooldown stays **6h**; research only — no VPS/paper change.

