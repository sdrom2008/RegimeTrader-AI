#!/usr/bin/env python3
"""Daily ETH sleeve. Separate from the 1h direction book.

Precommitted rules, no search:
- Buy and hold
- Long-only, weight = min(1, target_vol / 20d realized vol)
- Same weight, flat when the trailing 90-day return is negative

This sleeve does not open trend-paper orders and does not read the model.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPO, "data", "ETH_USDT_1h_6y.csv")
REPORT = os.path.join(REPO, "reports", "slow_sleeve_eth.md")

TARGET_ANN_VOL = 0.25
VOL_LOOKBACK = 20
TREND_LOOKBACK = 90
MAX_WEIGHT = 1.0
FEE = 0.0004  # one-way, charged on absolute weight change


def load_daily() -> pd.DataFrame:
    raw = pd.read_csv(DATA, index_col="timestamp", parse_dates=True).sort_index()
    daily = raw.resample("1D").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    return daily.dropna(subset=["Close"])


def stats(name: str, rets: pd.Series) -> dict:
    r = rets.dropna()
    equity = (1.0 + r).cumprod()
    peak = equity.cummax()
    dd = (equity / peak - 1.0).min()
    ann = float((1.0 + r.mean()) ** 365 - 1.0) if len(r) else 0.0
    vol = float(r.std() * np.sqrt(365)) if len(r) else 0.0
    sharpe = float(r.mean() / r.std() * np.sqrt(365)) if r.std() and len(r) else 0.0
    return {
        "name": name,
        "ann": ann,
        "vol": vol,
        "sharpe": sharpe,
        "max_dd": float(dd) if len(r) else 0.0,
        "final": float(equity.iloc[-1]) if len(equity) else 1.0,
        "days": int(len(r)),
    }


def simulate(weight: pd.Series, ret: pd.Series) -> pd.Series:
    # Weight decided at the prior close. Cost is charged when the weight changes.
    w = weight.shift(1).fillna(0.0)
    turnover = w.diff().abs()
    turnover.iloc[0] = abs(float(w.iloc[0]))
    return w * ret - turnover * FEE


def row(s: dict) -> str:
    return (
        f"| {s['name']} | {s['ann']*100:.1f}% | {s['vol']*100:.1f}% | {s['sharpe']:.2f} | "
        f"{s['max_dd']*100:.1f}% | {s['final']:.2f}x | {s['days']} |"
    )


def main():
    daily = load_daily()
    ret = daily["Close"].pct_change()
    rv = ret.rolling(VOL_LOOKBACK).std() * np.sqrt(365)
    vol_w = (TARGET_ANN_VOL / rv).clip(lower=0.0, upper=MAX_WEIGHT)
    mom = daily["Close"].pct_change(TREND_LOOKBACK)
    trend_w = vol_w.where(mom > 0, 0.0)

    hold = stats("Buy and hold", ret)
    vol = stats("Vol target 25%", simulate(vol_w, ret))
    trend = stats("Vol target + 90d long/flat", simulate(trend_w, ret))

    lines = [
        "# ETH daily sleeve",
        "",
        f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}",
        f"- Data: `{os.path.basename(DATA)}` resampled to 1D, {daily.index.min().date()} → {daily.index.max().date()}",
        f"- Vol target **{TARGET_ANN_VOL:.0%}**, lookback **{VOL_LOOKBACK}** days, weight cap **{MAX_WEIGHT:.0f}**.",
        f"- Trend filter: trailing **{TREND_LOOKBACK}** day return. Flat when it is negative.",
        f"- Cost: **{FEE*10000:.0f} bps** on the change in weight. No funding, no model, no 1h gates.",
        "- Sharpe uses a zero risk-free rate and 365-day scaling. This is one full sample, not a walk-forward.",
        "- Not combined with the direction sleeve. A higher Sharpe here is not permission to size it up inside `paper_trader.py`.",
        "",
        "| Sleeve | Ann. return | Ann. vol | Sharpe | Max DD | Growth of $1 | Days |",
        "|--------|-------------|----------|--------|--------|--------------|------|",
        row(hold),
        row(vol),
        row(trend),
        "",
        "The question this file answers is whether a slow ETH book earns its keep against just holding ETH.",
        "It does not answer whether the 1h model should be replaced.",
        "",
    ]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[+] {REPORT}")
    for s in (hold, vol, trend):
        print(
            f"{s['name']}: ann={s['ann']*100:.1f}% sharpe={s['sharpe']:.2f} "
            f"dd={s['max_dd']*100:.1f}% final={s['final']:.2f}x"
        )


if __name__ == "__main__":
    main()
