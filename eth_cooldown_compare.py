#!/usr/bin/env python3
"""ETH walk-forward: cooldown 6h vs 0h (paired, same fold models).

Trains the model once per fold, then simulates both cooldown settings on the
same predictions so the only free variable is cooldown_bars.

Writes reports/eth_model_vs_rule_no_cooldown.md by default.
Does not change config.py paper/live defaults (still 6h).
"""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from eth_model_vs_rule import rule_preds
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

DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "reports",
    "eth_model_vs_rule_no_cooldown.md",
)

# Published aggregate from reports/eth_model_vs_rule.md (generated 2026-10-26 03:26 UTC).
# Fold calendar there was 2021-10-27→2026-10-01; current data/features yield a shifted
# calendar, so those numbers are cited as history, not re-simulated here.
PUBLISHED_6H = {
    "oos": "2021-10-27→2026-10-01",
    "oos_days": 1800,
    "Model": {"n": 117, "wr": 0.487, "pf": 1.74, "pnl": 8266.0},
    "Rule": {"n": 544, "wr": 0.404, "pf": 1.15, "pnl": 9362.0},
}


def reason_counts(trades) -> str:
    c = Counter(t.reason for t in trades)
    if not c:
        return "—"
    return ", ".join(f"{k} {v}" for k, v in sorted(c.items()))


def ann_trades(n: int, oos_days: int) -> float:
    return n / (oos_days / 365.25)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETH WF paired cooldown contrast (6h vs 0h)"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=DEFAULT_OUT,
        help="Report markdown path",
    )
    parser.add_argument(
        "--cooldown-on",
        type=int,
        default=MIN_BARS_BETWEEN_TRADES,
        help="Bars for the 'with cooldown' arm (default: config MIN_BARS_BETWEEN_TRADES)",
    )
    parser.add_argument(
        "--cooldown-off",
        type=int,
        default=0,
        help="Bars for the 'no cooldown' arm (default: 0)",
    )
    args = parser.parse_args()
    report_path = args.out
    if not os.path.isabs(report_path):
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), report_path
        )
    cd_on = int(args.cooldown_on)
    cd_off = int(args.cooldown_off)

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
        cd_on: {"m": [], "r": [], "ms": 0, "rs": 0, "mdd": [], "rdd": []},
        cd_off: {"m": [], "r": [], "ms": 0, "rs": 0, "mdd": [], "rdd": []},
    }
    fold_lines = []

    # Deterministic RF within this process (paired sims share the fit).
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
        r_preds = rule_preds(test_df)
        r_confs = np.ones(len(test_df), dtype=float)

        row_bits = [
            f"| {fid} | {test_df.index.min().date()}→{test_df.index.max().date()}"
        ]
        for cd in (cd_on, cd_off):
            m_tr, m_eq, m_dd, m_sig = simulate_fold(
                "ETH", fid, test_df, preds, confs, cooldown_bars=cd
            )
            r_tr, r_eq, r_dd, r_sig = simulate_fold(
                "ETH", fid, test_df, r_preds, r_confs, cooldown_bars=cd
            )
            buckets[cd]["m"].extend(m_tr)
            buckets[cd]["r"].extend(r_tr)
            buckets[cd]["ms"] += m_sig
            buckets[cd]["rs"] += r_sig
            buckets[cd]["mdd"].append(m_dd)
            buckets[cd]["rdd"].append(r_dd)
            m_sm = summarize_trades(m_tr)
            r_sm = summarize_trades(r_tr)
            row_bits.append(
                f" | {m_sm['n_trades']} | {pf_str(m_sm['profit_factor'])} | "
                f"{(m_eq / INITIAL_CAPITAL - 1) * 100:+.1f}% | "
                f"{r_sm['n_trades']} | {pf_str(r_sm['profit_factor'])} | "
                f"{(r_eq / INITIAL_CAPITAL - 1) * 100:+.1f}%"
            )
        fold_lines.append("".join(row_bits) + " |")
        m6 = summarize_trades(
            [t for t in buckets[cd_on]["m"] if t.fold_id == fid]
        )
        m0 = summarize_trades(
            [t for t in buckets[cd_off]["m"] if t.fold_id == fid]
        )
        print(
            f"  fold {fid}: model cd{cd_on}={m6['n_trades']} PF={pf_str(m6['profit_factor'])} | "
            f"cd{cd_off}={m0['n_trades']} PF={pf_str(m0['profit_factor'])}"
        )

    elapsed = time.time() - t0
    pub_years = PUBLISHED_6H["oos_days"] / 365.25

    def row(label: str, sm: dict, n: int) -> str:
        return (
            f"| {label} | {n} | {sm['win_rate']*100:.1f}% | {pf_str(sm['profit_factor'])} | "
            f"{ann_trades(n, oos_days):.1f} | ${sm['total_pnl']:,.0f} |"
        )

    m_on = summarize_trades(buckets[cd_on]["m"])
    m_off = summarize_trades(buckets[cd_off]["m"])
    r_on = summarize_trades(buckets[cd_on]["r"])
    r_off = summarize_trades(buckets[cd_off]["r"])

    lines = [
        "# ETH walk-forward: cooldown 6h vs 0h",
        "",
        f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}",
        "- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.",
        f"- Paired sim: one RandomForest fit per fold (`n_jobs=1`, seed 42), then "
        f"`simulate_fold(..., cooldown_bars={cd_on})` vs `cooldown_bars={cd_off}`.",
        "- Gates / exits: ADX≥35, conf≥0.80, |DI|≥15, SL 1.5×ATR, TP 2.5R, trail@99R, "
        "max hold 24h, fee 4bps×2, slip 2bps.",
        f"- **Research sets cooldown_off={cd_off}.** Paper / live default remains "
        f"`MIN_BARS_BETWEEN_TRADES={MIN_BARS_BETWEEN_TRADES}` / `COOLDOWN_HOURS=6` "
        "(config.py untouched).",
        f"- This-run OOS: **{oos_start.date()} → {oos_end.date()}** "
        f"= {oos_days} days ≈ {years:.4f} years.",
        f"- Runtime: {elapsed:.0f}s",
        "",
        "## Aggregate contrast (paired, this environment)",
        "",
        "| Arm | Cooldown | Trades | WR | PF | Ann. trades | Sum PnL |",
        "|-----|----------|--------|----|----|-------------|---------|",
        (
            f"| Model | {cd_on}h | {m_on['n_trades']} | {m_on['win_rate']*100:.1f}% | "
            f"{pf_str(m_on['profit_factor'])} | {ann_trades(m_on['n_trades'], oos_days):.1f} | "
            f"${m_on['total_pnl']:,.0f} |"
        ),
        (
            f"| Model | {cd_off}h | {m_off['n_trades']} | {m_off['win_rate']*100:.1f}% | "
            f"{pf_str(m_off['profit_factor'])} | {ann_trades(m_off['n_trades'], oos_days):.1f} | "
            f"${m_off['total_pnl']:,.0f} |"
        ),
        (
            f"| Rule | {cd_on}h | {r_on['n_trades']} | {r_on['win_rate']*100:.1f}% | "
            f"{pf_str(r_on['profit_factor'])} | {ann_trades(r_on['n_trades'], oos_days):.1f} | "
            f"${r_on['total_pnl']:,.0f} |"
        ),
        (
            f"| Rule | {cd_off}h | {r_off['n_trades']} | {r_off['win_rate']*100:.1f}% | "
            f"{pf_str(r_off['profit_factor'])} | {ann_trades(r_off['n_trades'], oos_days):.1f} | "
            f"${r_off['total_pnl']:,.0f} |"
        ),
        "",
        f"Ann. trades = total trades / ({oos_days}/365.25).",
        "",
        "## Exit reasons (paired)",
        "",
        f"- Model {cd_on}h: {reason_counts(buckets[cd_on]['m'])}",
        f"- Model {cd_off}h: {reason_counts(buckets[cd_off]['m'])}",
        f"- Rule {cd_on}h: {reason_counts(buckets[cd_on]['r'])}",
        f"- Rule {cd_off}h: {reason_counts(buckets[cd_off]['r'])}",
        "",
        "## Published 6h baseline (historical cite)",
        "",
        f"From `reports/eth_model_vs_rule.md` (UTC 2026-10-26 03:26), OOS "
        f"{PUBLISHED_6H['oos']} = {PUBLISHED_6H['oos_days']}d ≈ {pub_years:.4f}y. "
        "Fold calendar differs under the current feature pipeline on this box, "
        "so these are **not** re-simulated here; cited for Boss's ~1.7 PF reference.",
        "",
        "| Arm | Cooldown | Trades | WR | PF | Ann. trades | Sum PnL |",
        "|-----|----------|--------|----|----|-------------|---------|",
        (
            f"| Model | 6h | {PUBLISHED_6H['Model']['n']} | "
            f"{PUBLISHED_6H['Model']['wr']*100:.1f}% | {PUBLISHED_6H['Model']['pf']:.2f} | "
            f"{ann_trades(PUBLISHED_6H['Model']['n'], PUBLISHED_6H['oos_days']):.1f} | "
            f"${PUBLISHED_6H['Model']['pnl']:,.0f} |"
        ),
        (
            f"| Rule | 6h | {PUBLISHED_6H['Rule']['n']} | "
            f"{PUBLISHED_6H['Rule']['wr']*100:.1f}% | {PUBLISHED_6H['Rule']['pf']:.2f} | "
            f"{ann_trades(PUBLISHED_6H['Rule']['n'], PUBLISHED_6H['oos_days']):.1f} | "
            f"${PUBLISHED_6H['Rule']['pnl']:,.0f} |"
        ),
        "",
        "## Per fold (M/R at 6h, then M/R at 0h)",
        "",
        "| Fold | Test | M6 n | M6 PF | M6 ret | R6 n | R6 PF | R6 ret | M0 n | M0 PF | M0 ret | R0 n | R0 PF | R0 ret |",
        "|------|------|------|-------|--------|------|-------|--------|------|-------|--------|------|-------|--------|",
        *fold_lines,
        "",
        "## Read this",
        "",
        f"- Model: cooldown off lifts trades {m_on['n_trades']} → {m_off['n_trades']} "
        f"but PF {pf_str(m_on['profit_factor'])} → {pf_str(m_off['profit_factor'])} "
        f"and Sum PnL ${m_on['total_pnl']:,.0f} → ${m_off['total_pnl']:,.0f}.",
        f"- Rule: trades {r_on['n_trades']} → {r_off['n_trades']}; "
        f"PF {pf_str(r_on['profit_factor'])} → {pf_str(r_off['profit_factor'])}; "
        f"Sum PnL ${r_on['total_pnl']:,.0f} → ${r_off['total_pnl']:,.0f}.",
        "- Repro: `python eth_cooldown_compare.py` or "
        "`python eth_model_vs_rule.py --cooldown 0 --out reports/eth_model_vs_rule_no_cooldown.md` "
        "(single-arm only).",
        "- Paper default cooldown stays **6h**; research only — no VPS/paper change.",
        "",
    ]

    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[+] {report_path}")
    print(
        f"MODEL {cd_on}h n={m_on['n_trades']} WR={m_on['win_rate']*100:.1f}% "
        f"PF={pf_str(m_on['profit_factor'])} ann={ann_trades(m_on['n_trades'], oos_days):.1f} "
        f"pnl=${m_on['total_pnl']:,.0f}"
    )
    print(
        f"MODEL {cd_off}h n={m_off['n_trades']} WR={m_off['win_rate']*100:.1f}% "
        f"PF={pf_str(m_off['profit_factor'])} ann={ann_trades(m_off['n_trades'], oos_days):.1f} "
        f"pnl=${m_off['total_pnl']:,.0f}"
    )
    print(
        f"RULE  {cd_on}h n={r_on['n_trades']} WR={r_on['win_rate']*100:.1f}% "
        f"PF={pf_str(r_on['profit_factor'])} ann={ann_trades(r_on['n_trades'], oos_days):.1f} "
        f"pnl=${r_on['total_pnl']:,.0f}"
    )
    print(
        f"RULE  {cd_off}h n={r_off['n_trades']} WR={r_off['win_rate']*100:.1f}% "
        f"PF={pf_str(r_off['profit_factor'])} ann={ann_trades(r_off['n_trades'], oos_days):.1f} "
        f"pnl=${r_off['total_pnl']:,.0f}"
    )


if __name__ == "__main__":
    main()
