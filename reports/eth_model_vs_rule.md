# ETH walk-forward: model vs ADX/DI rule

- Generated (UTC): 2026-10-26 03:26
- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.
- Same bars, same simulator (`walk_forward_v1.simulate_fold`): SL 1.5×ATR, TP 2.5R, trail@99R, cooldown 6h, max hold 24h, fee 4bps both sides, slippage 2bps.
- **Model:** retrain RandomForest each fold (120 trees, depth 14). Enter only if ADX≥35, confidence≥0.80, |DI|≥15, and the predicted class agrees with DI.
- **Rule:** no model. Enter when ADX≥35 and |DI|≥15. Long if +DI>−DI, short if −DI>+DI.
- Runtime: 6s

## Aggregate

| Arm | Signals | Trades | WR | PF | Sum PnL | Naive ret | Avg hold | Mean fold DD |
|-----|---------|--------|----|----|---------|-----------|----------|---------------|
| Model | 292 | 117 | 48.7% | 1.74 | $8,266 | +82.7% | 14.0h | 5.2% |
| Rule | 1751 | 544 | 40.4% | 1.15 | $9,362 | +93.6% | 13.6h | 13.6% |

Naive return is the sum of fold PnL divided by $10,000. Folds are not compounded.

## Exit reasons

- Model: MAX_HOLD 34, SL/TRAIL 51, TP 32
- Rule: EOD 3, MAX_HOLD 150, SL/TRAIL 281, TP 110

## Per fold

| Fold | Test | Acc | M sig | M trades | M PF | M ret | M DD | R sig | R trades | R PF | R ret | R DD |
|------|------|-----|-------|----------|------|-------|------|-------|----------|------|-------|------|
| 0 | 2021-10-27→2022-01-25 | 75.4% | 1 | 1 | inf | +4.2% | 0.6% | 46 | 32 | 1.21 | +5.9% | 15.2% |
| 1 | 2022-01-25→2022-04-25 | 70.1% | 11 | 10 | 0.70 | -4.6% | 9.1% | 49 | 29 | 0.71 | -11.9% | 15.0% |
| 2 | 2022-04-25→2022-07-24 | 74.3% | 5 | 5 | 5.31 | +12.4% | 4.0% | 41 | 29 | 1.83 | +24.1% | 5.7% |
| 3 | 2022-07-24→2022-10-22 | 63.2% | 6 | 6 | 3.26 | +9.9% | 2.7% | 54 | 27 | 1.23 | +6.2% | 15.4% |
| 4 | 2022-10-22→2023-01-20 | 72.5% | 8 | 5 | 1.28 | +1.0% | 3.7% | 95 | 19 | 0.65 | -8.9% | 11.3% |
| 5 | 2023-01-20→2023-04-20 | 66.5% | 20 | 12 | 1.31 | +3.4% | 11.1% | 107 | 28 | 0.70 | -12.3% | 22.3% |
| 6 | 2023-04-20→2023-07-19 | 72.6% | 6 | 2 | 2.21 | +2.5% | 2.5% | 109 | 14 | 0.68 | -6.7% | 12.8% |
| 7 | 2023-07-19→2023-10-17 | 64.7% | 33 | 4 | 2.13 | +2.2% | 3.3% | 203 | 13 | 0.66 | -4.7% | 7.1% |
| 8 | 2023-10-17→2024-01-15 | 70.5% | 24 | 2 | 0.29 | -1.6% | 3.7% | 98 | 28 | 1.37 | +7.8% | 10.4% |
| 9 | 2024-01-15→2024-04-14 | 75.6% | 0 | 0 | 0.00 | +0.0% | 0.0% | 98 | 34 | 1.18 | +5.4% | 16.1% |
| 10 | 2024-04-14→2024-07-13 | 67.8% | 18 | 4 | 2.25 | +5.2% | 2.4% | 126 | 34 | 0.98 | -2.4% | 11.0% |
| 11 | 2024-07-13→2024-10-11 | 70.0% | 10 | 7 | 0.38 | -7.9% | 9.1% | 82 | 32 | 0.86 | -7.5% | 19.1% |
| 12 | 2024-10-11→2025-01-09 | 73.5% | 12 | 4 | 4.25 | +7.2% | 5.6% | 74 | 31 | 1.75 | +26.0% | 8.4% |
| 13 | 2025-01-09→2025-04-09 | 71.4% | 19 | 11 | 0.60 | -6.4% | 13.1% | 80 | 35 | 0.44 | -26.2% | 32.7% |
| 14 | 2025-04-09→2025-07-08 | 71.5% | 8 | 5 | 15.52 | +14.6% | 3.2% | 59 | 31 | 1.24 | +6.7% | 10.3% |
| 15 | 2025-07-08→2025-10-06 | 70.8% | 27 | 11 | 10.75 | +25.0% | 4.1% | 81 | 31 | 2.03 | +28.6% | 9.6% |
| 16 | 2025-10-06→2026-01-04 | 73.6% | 5 | 4 | 0.30 | -4.4% | 7.3% | 74 | 24 | 0.69 | -11.1% | 15.3% |
| 17 | 2026-01-04→2026-04-04 | 68.9% | 10 | 7 | 8.25 | +14.6% | 3.4% | 93 | 30 | 2.23 | +33.9% | 9.2% |
| 18 | 2026-04-04→2026-07-03 | 67.2% | 23 | 5 | 3.35 | +10.3% | 4.2% | 97 | 23 | 1.84 | +20.8% | 12.0% |
| 19 | 2026-07-03→2026-10-01 | 64.8% | 46 | 12 | 0.35 | -11.3% | 11.5% | 85 | 20 | 0.72 | -8.0% | 12.4% |

## Read this

- The rule is the control. The model is useful only if its profit factor is higher after it skips trades.
- A model entry has to pass the same ADX and |DI| gates, so it cannot take a trade the rule would reject on those two filters. Paths still diverge once a position or a cooldown is open.
- This is one symbol, reset-capital folds, no funding, and a lighter forest than the deployed pickle.

