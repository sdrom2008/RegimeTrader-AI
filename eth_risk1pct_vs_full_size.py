#!/usr/bin/env python3
"""ETH walk-forward: model arm 1% risk vs full-size (paired, same fold models).

Trains the model once per fold, then simulates both sizing modes on the same
predictions so the only free variable is position sizing.

Arm A (risk): RISK_PER_TRADE_PCT=0.01, then cap at equity*LEVERAGE (default path).
Arm B (full): amount = (equity * LEVERAGE) / entry_price — no 1% risk shrink.

Writes reports/eth_risk1pct_vs_full_size.md by default.
Does not change config.py paper/live defaults (still RISK=0.01, LEVERAGE=2, cooldown=6).
"""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from walk_forward_v1 import (
    FEATURE_COLS,
    INITIAL_CAPITAL,
    LOOK_FORWARD,
    MIN_BARS_BETWEEN_TRADES,
    RF_PARAMS,
    load_ohlcv,
    make_fold_windows,
    pf_str,
    simulate_fold,
    summarize_trades,
)
from strategy_v2_quantile import label_data_3class_quantile, prepare_features_v2
from config import LEVERAGE, RISK_PER_TRADE_PCT

DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reports",
    "eth_risk1pct_vs_full_size.md",
)

ARMS = (
    ("risk", "A 1% risk", {"sizing": "risk", "risk_per_trade_pct": 0.01}),
    ("full", "B full size", {"sizing": "full"}),
)


def reason_counts(trades) -> str:
    c = Counter(t.reason for t in trades)
    if not c:
        return "—"
    return ", ".join(f"{k} {v}" for k, v in sorted(c.items()))


def ann_trades(n: int, oos_days: int) -> float:
    return n / (oos_days / 365.25)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETH WF paired 1% risk vs full-size contrast (model arm)"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=DEFAULT_OUT,
        help="Report markdown path",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=MIN_BARS_BETWEEN_TRADES,
        help="Cooldown bars (default: config MIN_BARS_BETWEEN_TRADES=6)",
    )
    args = parser.parse_args()
    report_path = args.out
    if not os.path.isabs(report_path):
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), report_path
        )
    cooldown = int(args.cooldown)

    t0 = time.time()
    raw = load_ohlcv("ETH")
    df = prepare_features_v2(raw.copy())
    df = label_data_3class_quantile(df)
    df = df.loc[df["High"].shift(-LOOK_FORWARD).notna()].copy()
    windows = make_fold_windows(df.index, 365, 90, 90)
    oos_start = windows[0][2]
    oos_end = windows[-1][3]
    oos_days = int((oos_end - oos_start).days)
    years = oos_days / 365.25
    print(
        f"[ETH] bars={len(df)} folds={len(windows)} "
        f"OOS {oos_start.date()} → {oos_end.date()} ({oos_days}d / {years:.4f}y)"
    )

    buckets = {
        key: {"trades": [], "sigs": 0, "dds": [], "eqs": [], "fold_rows": []}
        for key, _, _ in ARMS
    }
    fold_lines = []

    rf_params = dict(RF_PARAMS)
    rf_params["n_jobs"] = 1

    for fid, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
        train_cut = tr_e - pd.Timedelta(hours=LOOK_FORWARD + 60)
        train_df = df.loc[(df.index >= tr_s) & (df.index < train_cut)]
        test_df = df.loc[(df.index >= te_s) & (df.index < te_e)]
        if len(train_df) < 500 or len(test_df) < 100:
            print(f"  fold {fid}: skip")
            continue

        model = RandomForestClassifier(**rf_params)
        model.fit(train_df[FEATURE_COLS], train_df["regime"].astype(int))
        preds = model.predict(test_df[FEATURE_COLS])
        probs = model.predict_proba(test_df[FEATURE_COLS])
        classes = list(model.classes_)
        confs = np.array(
            [probs[i, classes.index(preds[i])] for i in range(len(preds))]
        )

        row_bits = [
            f"| {fid} | {test_df.index.min().date()}→{test_df.index.max().date()}"
        ]
        print_bits = []
        for key, label, kwargs in ARMS:
            tr, eq, dd, sig = simulate_fold(
                "ETH",
                fid,
                test_df,
                preds,
                confs,
                cooldown_bars=cooldown,
                **kwargs,
            )
            buckets[key]["trades"].extend(tr)
            buckets[key]["sigs"] += sig
            buckets[key]["dds"].append(dd)
            buckets[key]["eqs"].append(eq)
            sm = summarize_trades(tr)
            ret_pct = (eq / INITIAL_CAPITAL - 1) * 100
            buckets[key]["fold_rows"].append(
                {
                    "fid": fid,
                    "test": f"{test_df.index.min().date()}→{test_df.index.max().date()}",
                    "n": sm["n_trades"],
                    "pf": sm["profit_factor"],
                    "ret": ret_pct,
                    "dd": dd,
                    "pnl": sm["total_pnl"],
                }
            )
            row_bits.append(
                f" | {sm['n_trades']} | {pf_str(sm['profit_factor'])} | "
                f"{ret_pct:+.1f}% | {dd:.1f}%"
            )
            print_bits.append(
                f"{key}={sm['n_trades']} PF={pf_str(sm['profit_factor'])} "
                f"ret={ret_pct:+.1f}% dd={dd:.1f}%"
            )
        fold_lines.append("".join(row_bits) + " |")
        print(f"  fold {fid}: " + " | ".join(print_bits))

    elapsed = time.time() - t0
    a = summarize_trades(buckets["risk"]["trades"])
    b = summarize_trades(buckets["full"]["trades"])
    a_dd = float(np.mean(buckets["risk"]["dds"])) if buckets["risk"]["dds"] else 0.0
    b_dd = float(np.mean(buckets["full"]["dds"])) if buckets["full"]["dds"] else 0.0

    lines = [
        "# ETH walk-forward: model arm 1% risk vs full size",
        "",
        f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}",
        "- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.",
        f"- Paired sim: one RandomForest fit per fold (`n_jobs=1`, seed 42 via RF_PARAMS), then "
        f"`simulate_fold(..., cooldown_bars={cooldown}, sizing='risk'|'full')`.",
        "- Gates / exits: ADX≥35, conf≥0.80, |DI|≥15, SL 1.5×ATR, TP 2.5R, trail@99R, "
        f"cooldown {cooldown}h, max hold 24h, fee 4bps×2, slip 2bps.",
        f"- Config defaults (untouched): `RISK_PER_TRADE_PCT={RISK_PER_TRADE_PCT}`, "
        f"`LEVERAGE={LEVERAGE}`, `MIN_BARS_BETWEEN_TRADES={MIN_BARS_BETWEEN_TRADES}`.",
        f"- This-run OOS: **{oos_start.date()} → {oos_end.date()}** "
        f"= {oos_days} days ≈ {years:.4f} years.",
        f"- Runtime: {elapsed:.0f}s",
        "",
        "## Full-size code definition",
        "",
        "In `walk_forward_v1.simulate_fold` (entry sizing block):",
        "",
        "- **Arm A `sizing='risk'`** (default / paper-like):",
        "  `risk_amount = equity * risk_per_trade_pct` (here 0.01);",
        "  `amount = risk_amount / abs(entry - SL)`;",
        "  then `max_notional = equity * LEVERAGE` (LEVERAGE=2) caps notional.",
        "- **Arm B `sizing='full'`**: skip the 1% risk shrink; target",
        "  `notional = equity * LEVERAGE`, then shrink to",
        "  `balance / (1/LEVERAGE + FEE_RATE)` so `margin + entry_fee` fits",
        "  (pure max_notional is otherwise unopenable by ~LEVERAGE×4bps of fee).",
        "  Code: `walk_forward_v1.simulate_fold` entry block, `sizing=='full'`.",
        "  Slippage / fee rates / margin check otherwise identical to the risk path.",
        "- Optional kwargs `risk_per_trade_pct` / `sizing` default to config behavior;",
        "  callers that omit them are unchanged.",
        "",
        "## Aggregate contrast (paired, model arm only)",
        "",
        "| Arm | Sizing | Trades | WR | PF | Ann. trades | Sum PnL | Mean fold MaxDD |",
        "|-----|--------|--------|----|----|-------------|---------|-----------------|",
        (
            f"| A | 1% risk | {a['n_trades']} | {a['win_rate']*100:.1f}% | "
            f"{pf_str(a['profit_factor'])} | {ann_trades(a['n_trades'], oos_days):.1f} | "
            f"${a['total_pnl']:,.0f} | {a_dd:.1f}% |"
        ),
        (
            f"| B | full (2× notional) | {b['n_trades']} | {b['win_rate']*100:.1f}% | "
            f"{pf_str(b['profit_factor'])} | {ann_trades(b['n_trades'], oos_days):.1f} | "
            f"${b['total_pnl']:,.0f} | {b_dd:.1f}% |"
        ),
        "",
        f"Ann. trades = total trades / ({oos_days}/365.25).",
        "",
        "## Exit reasons",
        "",
        f"- Arm A (1% risk): {reason_counts(buckets['risk']['trades'])}",
        f"- Arm B (full): {reason_counts(buckets['full']['trades'])}",
        "",
        "## Per fold (same preds/confs)",
        "",
        "| Fold | Test | A n | A PF | A ret | A MaxDD | B n | B PF | B ret | B MaxDD |",
        "|------|------|-----|------|-------|---------|-----|------|-------|---------|",
        *fold_lines,
        "",
        "## Read this",
        "",
        (
            f"- Model arm: full size moves trades {a['n_trades']} → {b['n_trades']}, "
            f"WR {a['win_rate']*100:.1f}% → {b['win_rate']*100:.1f}%, "
            f"PF {pf_str(a['profit_factor'])} → {pf_str(b['profit_factor'])}, "
            f"Sum PnL ${a['total_pnl']:,.0f} → ${b['total_pnl']:,.0f}, "
            f"mean fold MaxDD {a_dd:.1f}% → {b_dd:.1f}%."
        ),
        "- Trade count can diverge slightly because larger PnL swings change equity "
        "and thus margin affordability / path; signals are still from the same preds.",
        "- Repro: `python eth_risk1pct_vs_full_size.py`",
        "- Paper / VPS defaults unchanged: RISK_PER_TRADE_PCT=0.01, LEVERAGE=2.0, cooldown=6h.",
        "",
    ]

    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[+] {report_path}")
    print(
        f"ARM A risk1% n={a['n_trades']} WR={a['win_rate']*100:.1f}% "
        f"PF={pf_str(a['profit_factor'])} ann={ann_trades(a['n_trades'], oos_days):.1f} "
        f"pnl=${a['total_pnl']:,.0f} meanDD={a_dd:.1f}%"
    )
    print(
        f"ARM B full   n={b['n_trades']} WR={b['win_rate']*100:.1f}% "
        f"PF={pf_str(b['profit_factor'])} ann={ann_trades(b['n_trades'], oos_days):.1f} "
        f"pnl=${b['total_pnl']:,.0f} meanDD={b_dd:.1f}%"
    )


if __name__ == "__main__":
    main()
