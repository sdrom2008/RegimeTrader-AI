# ETH funding carry sleeve

- Generated (UTC): 2026-10-26 04:24
- Symbol: ETHUSDT perpetual funding. 6649 prints, 2020-10-01 → 2026-10-26.
- Hedge: long spot, short perp, equal notional. Report PnL is **funding minus fees only**.
- Hurdle: **4%** annual. Round trip: **16 bps** (4 bps × 4 legs).
- Enter when the trailing 21 prints (about 7 days) sum more than fees plus one week of the hurdle.
- Exit when that trailing sum drops below one week of the hurdle.
- Basis, exchange outage, and a crowded unwind are not in this curve.
- Does not place orders and does not touch `paper_trade_state_v2.json`.

| Metric | Value |
|--------|-------|
| Opens | 7 |
| Time in market | 34.0% |
| Funding sum | 58.98% of notional |
| Fees paid | 1.12% of notional |
| Growth of $1 | 1.783x |
| Annualized (funding − fees) | 9.99% |
| Max drawdown of this curve | -0.39% |

If this annualized number is below the hurdle, the sleeve stays research-only.

