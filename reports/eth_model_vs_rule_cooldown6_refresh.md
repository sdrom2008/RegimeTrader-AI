# ETH walk-forward: model vs ADX/DI rule

- Generated (UTC): 2026-10-26 15:48
- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.
- Same bars, same simulator (`walk_forward_v1.simulate_fold`): SL 1.5×ATR, TP 2.5R, trail@99R, cooldown 6h, max hold 24h, fee 4bps both sides, slippage 2bps.
- **Model:** retrain RandomForest each fold (120 trees, depth 14). Enter only if ADX≥35, confidence≥0.80, |DI|≥15, and the predicted class agrees with DI.
- **Rule:** no model. Enter when ADX≥35 and |DI|≥15. Long if +DI>−DI, short if −DI>+DI.
- Runtime: 7s
- Cooldown: 6h (= config MIN_BARS_BETWEEN_TRADES).

## Aggregate

| Arm | Signals | Trades | WR | PF | Sum PnL | Naive ret | Avg hold | Mean fold DD |
|-----|---------|--------|----|----|---------|-----------|----------|---------------|
| Model | 105 | 80 | 43.8% | 1.29 | $1,235 | +12.4% | 12.8h | 2.1% |
| Rule | 1351 | 668 | 37.1% | 1.05 | $1,819 | +18.2% | 12.9h | 9.4% |

Naive return is the sum of fold PnL divided by $10,000. Folds are not compounded.

## Exit reasons

- Model: EOD 1, MAX_HOLD 23, SL/TRAIL 39, TP 17
- Rule: EOD 5, MAX_HOLD 154, SL/TRAIL 371, TP 138

## Per fold

| Fold | Test | Acc | M sig | M trades | M PF | M ret | M DD | R sig | R trades | R PF | R ret | R DD |
|------|------|-----|-------|----------|------|-------|------|-------|----------|------|-------|------|
| 0 | 2021-10-20→2022-01-18 | 79.8% | 0 | 0 | 0.00 | +0.0% | 0.0% | 47 | 32 | 1.06 | +0.5% | 10.1% |
| 1 | 2022-01-18→2022-04-18 | 78.9% | 3 | 2 | 0.03 | -1.0% | 2.0% | 38 | 30 | 0.72 | -6.1% | 7.5% |
| 2 | 2022-04-18→2022-07-17 | 81.3% | 1 | 1 | 0.00 | -1.0% | 1.3% | 38 | 28 | 2.05 | +13.2% | 2.9% |
| 3 | 2022-07-17→2022-10-15 | 70.3% | 2 | 2 | inf | +3.4% | 1.1% | 52 | 31 | 1.61 | +8.8% | 7.1% |
| 4 | 2022-10-15→2023-01-13 | 76.1% | 3 | 3 | 2.17 | +1.1% | 1.8% | 69 | 26 | 0.63 | -6.9% | 10.9% |
| 5 | 2023-01-13→2023-04-13 | 70.1% | 6 | 6 | 3.49 | +5.3% | 2.8% | 70 | 36 | 0.57 | -13.0% | 14.7% |
| 6 | 2023-04-13→2023-07-12 | 78.4% | 1 | 1 | inf | +0.5% | 0.4% | 56 | 28 | 0.69 | -7.4% | 11.6% |
| 7 | 2023-07-12→2023-10-10 | 69.8% | 2 | 2 | 0.46 | -0.7% | 1.3% | 116 | 37 | 1.11 | +0.2% | 7.1% |
| 8 | 2023-10-10→2024-01-08 | 72.4% | 3 | 2 | 0.32 | -0.8% | 1.2% | 76 | 40 | 0.37 | -17.8% | 18.7% |
| 9 | 2024-01-08→2024-04-07 | 78.9% | 0 | 0 | 0.00 | +0.0% | 0.0% | 81 | 41 | 1.43 | +9.3% | 7.6% |
| 10 | 2024-04-07→2024-07-06 | 71.9% | 4 | 4 | 0.75 | -1.0% | 2.9% | 99 | 43 | 0.64 | -10.8% | 15.4% |
| 11 | 2024-07-06→2024-10-04 | 75.6% | 6 | 5 | 0.58 | -1.9% | 3.2% | 76 | 35 | 0.75 | -6.7% | 10.0% |
| 12 | 2024-10-04→2025-01-02 | 79.4% | 6 | 6 | 3.22 | +4.9% | 1.5% | 67 | 33 | 1.48 | +8.7% | 4.2% |
| 13 | 2025-01-02→2025-04-02 | 73.5% | 11 | 9 | 0.02 | -7.3% | 7.4% | 72 | 35 | 0.43 | -14.7% | 20.2% |
| 14 | 2025-04-02→2025-07-01 | 80.5% | 0 | 0 | 0.00 | +0.0% | 0.0% | 60 | 34 | 1.50 | +8.2% | 5.3% |
| 15 | 2025-07-01→2025-09-29 | 69.8% | 7 | 7 | 2.06 | +2.4% | 2.4% | 73 | 39 | 1.62 | +10.7% | 4.9% |
| 16 | 2025-09-29→2025-12-28 | 75.9% | 4 | 4 | 0.70 | -0.7% | 3.0% | 50 | 26 | 0.79 | -4.4% | 6.8% |
| 17 | 2025-12-28→2026-03-28 | 76.1% | 8 | 5 | inf | +7.2% | 0.8% | 75 | 35 | 1.83 | +14.0% | 7.0% |
| 18 | 2026-03-28→2026-06-26 | 70.4% | 12 | 9 | 1.13 | +0.5% | 3.3% | 71 | 30 | 2.01 | +15.5% | 4.8% |
| 19 | 2026-06-26→2026-09-24 | 69.5% | 26 | 12 | 0.89 | -1.2% | 5.5% | 65 | 29 | 0.84 | -3.8% | 11.1% |

## Read this

- The rule is the control. The model is useful only if its profit factor is higher after it skips trades.
- A model entry has to pass the same ADX and |DI| gates, so it cannot take a trade the rule would reject on those two filters. Paths still diverge once a position or a cooldown is open.
- This is one symbol, reset-capital folds, no funding, and a lighter forest than the deployed pickle.

