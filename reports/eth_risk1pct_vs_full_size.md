# ETH walk-forward: model arm 1% risk vs full size

- Generated (UTC): 2026-10-26 16:26
- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.
- Paired sim: one RandomForest fit per fold (`n_jobs=1`, seed 42 via RF_PARAMS), then `simulate_fold(..., cooldown_bars=6, sizing='risk'|'full')`.
- Gates / exits: ADX≥35, conf≥0.80, |DI|≥15, SL 1.5×ATR, TP 2.5R, trail@99R, cooldown 6h, max hold 24h, fee 4bps×2, slip 2bps.
- Config defaults (untouched): `RISK_PER_TRADE_PCT=0.01`, `LEVERAGE=2.0`, `MIN_BARS_BETWEEN_TRADES=6`.
- This-run OOS: **2021-10-20 → 2026-09-24** = 1800 days ≈ 4.9281 years.
- Runtime: 29s

## Full-size code definition

In `walk_forward_v1.simulate_fold` (entry sizing block):

- **Arm A `sizing='risk'`** (default / paper-like):
  `risk_amount = equity * risk_per_trade_pct` (here 0.01);
  `amount = risk_amount / abs(entry - SL)`;
  then `max_notional = equity * LEVERAGE` (LEVERAGE=2) caps notional.
- **Arm B `sizing='full'`**: skip the 1% risk shrink; target
  `notional = equity * LEVERAGE`, then shrink to
  `balance / (1/LEVERAGE + FEE_RATE)` so `margin + entry_fee` fits
  (pure max_notional is otherwise unopenable by ~LEVERAGE×4bps of fee).
  Code: `walk_forward_v1.simulate_fold` entry block, `sizing=='full'`.
  Slippage / fee rates / margin check otherwise identical to the risk path.
- Optional kwargs `risk_per_trade_pct` / `sizing` default to config behavior;
  callers that omit them are unchanged.

## Aggregate contrast (paired, model arm only)

| Arm | Sizing | Trades | WR | PF | Ann. trades | Sum PnL | Mean fold MaxDD |
|-----|--------|--------|----|----|-------------|---------|-----------------|
| A | 1% risk | 80 | 43.8% | 1.29 | 16.2 | $1,235 | 2.1% |
| B | full (2× notional) | 84 | 42.9% | 1.03 | 17.0 | $477 | 7.6% |

Ann. trades = total trades / (1800/365.25).

## Exit reasons

- Arm A (1% risk): EOD 1, MAX_HOLD 23, SL/TRAIL 39, TP 17
- Arm B (full): EOD 1, MAX_HOLD 24, SL/TRAIL 42, TP 17

## Per fold (same preds/confs)

| Fold | Test | A n | A PF | A ret | A MaxDD | B n | B PF | B ret | B MaxDD |
|------|------|-----|------|-------|---------|-----|------|-------|---------|
| 0 | 2021-10-20→2022-01-18 | 0 | 0.00 | +0.0% | 0.0% | 0 | 0.00 | +0.0% | 0.0% |
| 1 | 2022-01-18→2022-04-18 | 2 | 0.03 | -1.0% | 2.0% | 2 | 0.07 | -4.1% | 11.8% |
| 2 | 2022-04-18→2022-07-17 | 1 | 0.00 | -1.0% | 1.3% | 1 | 0.00 | -15.3% | 18.3% |
| 3 | 2022-07-17→2022-10-15 | 2 | inf | +3.4% | 1.1% | 2 | inf | +14.6% | 5.9% |
| 4 | 2022-10-15→2023-01-13 | 3 | 2.17 | +1.1% | 1.8% | 3 | 0.80 | -2.4% | 13.3% |
| 5 | 2023-01-13→2023-04-13 | 6 | 3.49 | +5.3% | 2.8% | 6 | 3.65 | +14.6% | 8.4% |
| 6 | 2023-04-13→2023-07-12 | 1 | inf | +0.5% | 0.4% | 1 | inf | +1.4% | 1.2% |
| 7 | 2023-07-12→2023-10-10 | 2 | 0.46 | -0.7% | 1.3% | 2 | 0.53 | -1.1% | 2.5% |
| 8 | 2023-10-10→2024-01-08 | 2 | 0.32 | -0.8% | 1.2% | 2 | 0.43 | -1.1% | 1.9% |
| 9 | 2024-01-08→2024-04-07 | 0 | 0.00 | +0.0% | 0.0% | 0 | 0.00 | +0.0% | 0.0% |
| 10 | 2024-04-07→2024-07-06 | 4 | 0.75 | -1.0% | 2.9% | 4 | 1.05 | -0.1% | 4.3% |
| 11 | 2024-07-06→2024-10-04 | 5 | 0.58 | -1.9% | 3.2% | 5 | 0.59 | -5.7% | 9.7% |
| 12 | 2024-10-04→2025-01-02 | 6 | 3.22 | +4.9% | 1.5% | 6 | 3.09 | +9.9% | 4.1% |
| 13 | 2025-01-02→2025-04-02 | 9 | 0.02 | -7.3% | 7.4% | 9 | 0.02 | -21.5% | 21.8% |
| 14 | 2025-04-02→2025-07-01 | 0 | 0.00 | +0.0% | 0.0% | 0 | 0.00 | +0.0% | 0.0% |
| 15 | 2025-07-01→2025-09-29 | 7 | 2.06 | +2.4% | 2.4% | 7 | 1.90 | +4.0% | 5.2% |
| 16 | 2025-09-29→2025-12-28 | 4 | 0.70 | -0.7% | 3.0% | 4 | 0.33 | -12.1% | 21.1% |
| 17 | 2025-12-28→2026-03-28 | 5 | inf | +7.2% | 0.8% | 5 | inf | +21.3% | 3.2% |
| 18 | 2026-03-28→2026-06-26 | 9 | 1.13 | +0.5% | 3.3% | 9 | 1.18 | +2.0% | 7.3% |
| 19 | 2026-06-26→2026-09-24 | 12 | 0.89 | -1.2% | 5.5% | 16 | 0.68 | -6.3% | 12.1% |

## Read this

- Model arm: full size moves trades 80 → 84, WR 43.8% → 42.9%, PF 1.29 → 1.03, Sum PnL $1,235 → $477, mean fold MaxDD 2.1% → 7.6%.
- Trade count can diverge slightly because larger PnL swings change equity and thus margin affordability / path; signals are still from the same preds.
- Repro: `python eth_risk1pct_vs_full_size.py`
- Paper / VPS defaults unchanged: RISK_PER_TRADE_PCT=0.01, LEVERAGE=2.0, cooldown=6h.

