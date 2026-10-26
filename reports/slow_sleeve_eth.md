# ETH daily sleeve

- Generated (UTC): 2026-10-26 04:24
- Data: `ETH_USDT_1h_6y.csv` resampled to 1D, 2020-10-27 → 2026-10-26
- Vol target **25%**, lookback **20** days, weight cap **1**.
- Trend filter: trailing **90** day return. Flat when it is negative.
- Cost: **4 bps** on the change in weight. No funding, no model, no 1h gates.
- Sharpe uses a zero risk-free rate and 365-day scaling. This is one full sample, not a walk-forward.
- Not combined with the direction sleeve. A higher Sharpe here is not permission to size it up inside `paper_trader.py`.

| Sleeve | Ann. return | Ann. vol | Sharpe | Max DD | Growth of $1 | Days |
|--------|-------------|----------|--------|--------|--------------|------|
| Buy and hold | 79.7% | 77.0% | 0.76 | -79.3% | 5.73x | 2190 |
| Vol target 25% | 22.8% | 29.1% | 0.71 | -43.0% | 2.67x | 2190 |
| Vol target + 90d long/flat | 9.1% | 20.4% | 0.43 | -29.8% | 1.49x | 2190 |

The question this file answers is whether a slow ETH book earns its keep against just holding ETH.
It does not answer whether the 1h model should be replaced.

