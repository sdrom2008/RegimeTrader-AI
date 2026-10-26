#!/usr/bin/env python3
"""ETH-only walk-forward: current model gates vs an ADX/DI rule.

Both arms share the same bars, folds, costs, and exit rules.
The rule arm does not fit a model. Direction comes from DI.
The model arm is the same retrained forest and gates as walk_forward_v1.py.

Writes reports/eth_model_vs_rule.md
"""

from __future__ import annotations

import os
import time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from strategy_v2_quantile import label_data_3class_quantile, prepare_features_v2
from walk_forward_v1 import (
    FEATURE_COLS,
    INITIAL_CAPITAL,
    LOOK_FORWARD,
    RF_PARAMS,
    load_ohlcv,
    make_fold_windows,
    pf_str,
    simulate_fold,
    summarize_trades,
)

REPORT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reports", "eth_model_vs_rule.md"
)


def rule_preds(df: pd.DataFrame) -> np.ndarray:
    plus = df["+DI"].to_numpy(dtype=float)
    minus = df["-DI"].to_numpy(dtype=float)
    preds = np.ones(len(df), dtype=int)
    preds[plus > minus] = 2
    preds[minus > plus] = 0
    return preds


def reason_counts(trades) -> str:
    c = Counter(t.reason for t in trades)
    if not c:
        return "—"
    return ", ".join(f"{k} {v}" for k, v in sorted(c.items()))


def arm_row(name: str, trades, n_signals: int, fold_dds: list[float]) -> str:
    sm = summarize_trades(trades)
    mean_dd = float(np.mean(fold_dds)) if fold_dds else 0.0
    return (
        f"| {name} | {n_signals} | {sm['n_trades']} | {sm['win_rate']*100:.1f}% | "
        f"{pf_str(sm['profit_factor'])} | ${sm['total_pnl']:,.0f} | "
        f"{sm['return_pct']:+.1f}% | {sm['avg_bars_held']:.1f}h | {mean_dd:.1f}% |"
    )


def main():
    t0 = time.time()
    raw = load_ohlcv("ETH")
    df = prepare_features_v2(raw.copy())
    df = label_data_3class_quantile(df)
    df = df.loc[df["High"].shift(-LOOK_FORWARD).notna()].copy()
    windows = make_fold_windows(df.index, 365, 90, 90)
    print(f"[ETH] bars={len(df)} folds={len(windows)} {df.index.min()} → {df.index.max()}")

    model_trades = []
    rule_trades = []
    model_sigs = 0
    rule_sigs = 0
    model_dds = []
    rule_dds = []
    fold_lines = []

    for fid, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
        train_cut = tr_e - pd.Timedelta(hours=LOOK_FORWARD + 60)
        train_df = df.loc[(df.index >= tr_s) & (df.index < train_cut)]
        test_df = df.loc[(df.index >= te_s) & (df.index < te_e)]
        if len(train_df) < 500 or len(test_df) < 100:
            print(f"  fold {fid}: skip")
            continue

        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(train_df[FEATURE_COLS], train_df["regime"].astype(int))
        preds = model.predict(test_df[FEATURE_COLS])
        probs = model.predict_proba(test_df[FEATURE_COLS])
        classes = list(model.classes_)
        confs = np.array([probs[i, classes.index(preds[i])] for i in range(len(preds))])
        acc = float(accuracy_score(test_df["regime"].astype(int), preds))

        m_trades, m_eq, m_dd, m_sig = simulate_fold("ETH", fid, test_df, preds, confs)
        r_preds = rule_preds(test_df)
        r_confs = np.ones(len(test_df), dtype=float)
        r_trades, r_eq, r_dd, r_sig = simulate_fold("ETH", fid, test_df, r_preds, r_confs)

        model_trades.extend(m_trades)
        rule_trades.extend(r_trades)
        model_sigs += m_sig
        rule_sigs += r_sig
        model_dds.append(m_dd)
        rule_dds.append(r_dd)

        m_sm = summarize_trades(m_trades)
        r_sm = summarize_trades(r_trades)
        m_ret = (m_eq / INITIAL_CAPITAL - 1.0) * 100.0
        r_ret = (r_eq / INITIAL_CAPITAL - 1.0) * 100.0
        fold_lines.append(
            f"| {fid} | {test_df.index.min().date()}→{test_df.index.max().date()} | "
            f"{acc*100:.1f}% | {m_sig} | {m_sm['n_trades']} | {pf_str(m_sm['profit_factor'])} | "
            f"{m_ret:+.1f}% | {m_dd:.1f}% | {r_sig} | {r_sm['n_trades']} | "
            f"{pf_str(r_sm['profit_factor'])} | {r_ret:+.1f}% | {r_dd:.1f}% |"
        )
        print(
            f"  fold {fid}: model trades={m_sm['n_trades']} PF={pf_str(m_sm['profit_factor'])} "
            f"ret={m_ret:+.1f}% | rule trades={r_sm['n_trades']} PF={pf_str(r_sm['profit_factor'])} "
            f"ret={r_ret:+.1f}%"
        )

    elapsed = time.time() - t0
    m_all = summarize_trades(model_trades)
    r_all = summarize_trades(rule_trades)
    lines = [
        "# ETH walk-forward: model vs ADX/DI rule",
        "",
        f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}",
        "- Symbol: **ETH/USDT** only. Train 365d / test 90d / step 90d. Each fold resets to $10,000.",
        "- Same bars, same simulator (`walk_forward_v1.simulate_fold`): SL 1.5×ATR, TP 2.5R, trail@99R, cooldown 6h, max hold 24h, fee 4bps both sides, slippage 2bps.",
        "- **Model:** retrain RandomForest each fold (120 trees, depth 14). Enter only if ADX≥35, confidence≥0.80, |DI|≥15, and the predicted class agrees with DI.",
        "- **Rule:** no model. Enter when ADX≥35 and |DI|≥15. Long if +DI>−DI, short if −DI>+DI.",
        f"- Runtime: {elapsed:.0f}s",
        "",
        "## Aggregate",
        "",
        "| Arm | Signals | Trades | WR | PF | Sum PnL | Naive ret | Avg hold | Mean fold DD |",
        "|-----|---------|--------|----|----|---------|-----------|----------|---------------|",
        arm_row("Model", model_trades, model_sigs, model_dds),
        arm_row("Rule", rule_trades, rule_sigs, rule_dds),
        "",
        "Naive return is the sum of fold PnL divided by $10,000. Folds are not compounded.",
        "",
        "## Exit reasons",
        "",
        f"- Model: {reason_counts(model_trades)}",
        f"- Rule: {reason_counts(rule_trades)}",
        "",
        "## Per fold",
        "",
        "| Fold | Test | Acc | M sig | M trades | M PF | M ret | M DD | R sig | R trades | R PF | R ret | R DD |",
        "|------|------|-----|-------|----------|------|-------|------|-------|----------|------|-------|------|",
        *fold_lines,
        "",
        "## Read this",
        "",
        "- The rule is the control. The model is useful only if its profit factor is higher after it skips trades.",
        "- A model entry has to pass the same ADX and |DI| gates, so it cannot take a trade the rule would reject on those two filters. Paths still diverge once a position or a cooldown is open.",
        "- This is one symbol, reset-capital folds, no funding, and a lighter forest than the deployed pickle.",
        "",
    ]
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[+] {REPORT_PATH}")
    print(
        f"MODEL trades={m_all['n_trades']} WR={m_all['win_rate']*100:.1f}% "
        f"PF={pf_str(m_all['profit_factor'])} pnl=${m_all['total_pnl']:,.0f}"
    )
    print(
        f"RULE  trades={r_all['n_trades']} WR={r_all['win_rate']*100:.1f}% "
        f"PF={pf_str(r_all['profit_factor'])} pnl=${r_all['total_pnl']:,.0f}"
    )


if __name__ == "__main__":
    main()
