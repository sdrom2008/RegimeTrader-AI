#!/usr/bin/env python3
"""ETH spot-long / perp-short funding carry. Separate from the trend book.

The position is hedged. PnL in this report is funding minus open/close fees.
Basis between spot and perp is not marked. Exchange failure and a crowded
unwind are not in the equity curve.

Entry (precommitted, not searched):
  trailing 21 funding prints (about 7 days) sum
  > round-trip fees + one week of the hurdle rate.
Exit when that same trailing sum no longer clears one week of the hurdle.

This script writes a report. It does not read or write paper_trade_state_v2.json.
"""

from __future__ import annotations

import json
import os
import urllib.request

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(REPO, "reports", "carry_sleeve_eth.md")
CACHE = os.path.join(REPO, "data", "ETHUSDT_funding.csv")

SYMBOL = "ETHUSDT"
# Spot taker + perp taker, open and close. 4 bps x 4 legs.
ROUND_TRIP_FEE = 0.0004 * 4
OPEN_FEE = ROUND_TRIP_FEE / 2
# Hurdle standing in for a T-bill. Not a live rate feed.
HURDLE_ANN = 0.04
PRINTS_7D = 21  # Binance funding is every 8 hours
URLS = (
    "https://fapi.binance.com/fapi/v1/fundingRate",
    "https://data-api.binance.vision/fapi/v1/fundingRate",
)


def fetch_funding() -> pd.DataFrame:
    start = int(pd.Timestamp("2020-10-01", tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp.now("UTC").timestamp() * 1000)
    rows = []
    used = None
    last_err = None
    for base in URLS:
        rows = []
        cursor = start
        try:
            while cursor < end:
                url = f"{base}?symbol={SYMBOL}&startTime={cursor}&endTime={end}&limit=1000"
                with urllib.request.urlopen(url, timeout=30) as resp:
                    batch = json.loads(resp.read().decode("utf-8"))
                if not batch:
                    break
                rows.extend(batch)
                nxt = int(batch[-1]["fundingTime"]) + 1
                if nxt <= cursor:
                    break
                cursor = nxt
                if len(batch) < 1000:
                    break
            if rows:
                used = base
                break
        except Exception as exc:
            last_err = exc
            rows = []
    if not rows:
        raise RuntimeError(f"funding history unavailable: {last_err}")
    df = pd.DataFrame(rows)
    df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df.drop_duplicates("fundingTime").sort_values("fundingTime")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    df.to_csv(CACHE, index=False)
    print(f"[+] funding {len(df)} prints via {used}")
    return df


def simulate(df: pd.DataFrame) -> pd.DataFrame:
    rate = df["fundingRate"].to_numpy()
    trail = df["fundingRate"].rolling(PRINTS_7D).sum()
    hurdle_week = HURDLE_ANN * 7 / 365
    enter_at = ROUND_TRIP_FEE + hurdle_week
    in_pos = False
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    fees = 0.0
    funding = 0.0
    opens = 0
    curve = []
    for i, ts in enumerate(df["fundingTime"]):
        tsum = trail.iloc[i]
        if pd.notna(tsum):
            if not in_pos and tsum > enter_at:
                in_pos = True
                opens += 1
                fees += OPEN_FEE
                equity *= 1.0 - OPEN_FEE
            elif in_pos and tsum < hurdle_week:
                in_pos = False
                fees += OPEN_FEE
                equity *= 1.0 - OPEN_FEE
        if in_pos:
            funding += float(rate[i])
            equity *= 1.0 + float(rate[i])
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0)
        curve.append((ts, equity, in_pos))
    out = pd.DataFrame(curve, columns=["time", "equity", "in_pos"])
    out.attrs["fees"] = fees
    out.attrs["funding"] = funding
    out.attrs["opens"] = opens
    out.attrs["max_dd"] = max_dd
    return out


def main():
    df = fetch_funding()
    curve = simulate(df)
    days = max((curve["time"].iloc[-1] - curve["time"].iloc[0]).total_seconds() / 86400.0, 1.0)
    final = float(curve["equity"].iloc[-1])
    ann = final ** (365.0 / days) - 1.0
    in_mkt = float(curve["in_pos"].mean())
    lines = [
        "# ETH funding carry sleeve",
        "",
        f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}",
        f"- Symbol: {SYMBOL} perpetual funding. {len(df)} prints, {df['fundingTime'].iloc[0].date()} → {df['fundingTime'].iloc[-1].date()}.",
        f"- Hedge: long spot, short perp, equal notional. Report PnL is **funding minus fees only**.",
        f"- Hurdle: **{HURDLE_ANN:.0%}** annual. Round trip: **{ROUND_TRIP_FEE*10000:.0f} bps** (4 bps × 4 legs).",
        f"- Enter when the trailing {PRINTS_7D} prints (about 7 days) sum more than fees plus one week of the hurdle.",
        "- Exit when that trailing sum drops below one week of the hurdle.",
        "- Basis, exchange outage, and a crowded unwind are not in this curve.",
        "- Does not place orders and does not touch `paper_trade_state_v2.json`.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Opens | {curve.attrs['opens']} |",
        f"| Time in market | {in_mkt*100:.1f}% |",
        f"| Funding sum | {curve.attrs['funding']*100:.2f}% of notional |",
        f"| Fees paid | {curve.attrs['fees']*100:.2f}% of notional |",
        f"| Growth of $1 | {final:.3f}x |",
        f"| Annualized (funding − fees) | {ann*100:.2f}% |",
        f"| Max drawdown of this curve | {curve.attrs['max_dd']*100:.2f}% |",
        "",
        "If this annualized number is below the hurdle, the sleeve stays research-only.",
        "",
    ]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[+] {REPORT}")
    print(
        f"opens={curve.attrs['opens']} in_mkt={in_mkt*100:.1f}% "
        f"ann={ann*100:.2f}% dd={curve.attrs['max_dd']*100:.2f}%"
    )


if __name__ == "__main__":
    main()
