#!/usr/bin/env python3
"""
Walk-forward validation v1 for RegimeTrader-AI.

Rolling RF retrains on strategy_v2_quantile features/labels, then simulates
paper-like gated trades on each OOS test fold.

Defaults: train 365d / test 90d / step 90d
Gates: ADX>=25, conf>=0.72, DI filter, SL 1.5 ATR, TP 2.5R, trail@1R,
       slippage 2bps, fee 4bps (mirrors config / paper).

Usage:
  .venv/bin/python walk_forward_v1.py
  .venv/bin/python walk_forward_v1.py --symbols BTC,ETH
  .venv/bin/python walk_forward_v1.py --train-days 365 --test-days 90 --step-days 90
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

from config import (
    ADX_STRONG_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    MIN_DI_DIFF,
    LEVERAGE,
    RISK_PER_TRADE_PCT,
    STOP_LOSS_ATR_MULT,
    TAKE_PROFIT_RR,
    TRAILING_STOP_ATR,
    TRAIL_ACTIVATE_R,
    MIN_BARS_BETWEEN_TRADES,
    MAX_HOLD_HOURS,
    SLIPPAGE_BPS,
    SLIPPAGE_ATR_FRAC,
)
from strategy_v2_quantile import prepare_features_v2, label_data_3class_quantile

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
REPORT_PATH = os.path.join(REPO_ROOT, "reports", "walk_forward_v1.md")

DEFAULT_SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
INITIAL_CAPITAL = 10_000.0
FEE_RATE = 0.0004
LOOK_FORWARD = 24  # hours; drop from train end to avoid label leakage into test

FEATURE_COLS = [
    "ADX", "+DI", "-DI", "DI_diff",
    "MACD_hist", "MACD_hist_cross_up",
    "RSI", "ATR",
    "Price_vs_EMA200",
    "Volume_Change_Ratio",
    "EMA_50", "EMA_200",
    "ADX_strong", "ADX_weak",
    "+DI_cross_above_-DI", "-DI_cross_above_+DI",
    "MACD_hist_positive",
    "Price_std_20", "ATR_ratio", "Drawdown_20", "RSI_dev",
]

# Faster RF for many folds (still class_weight balanced)
RF_PARAMS = dict(
    n_estimators=120,
    max_depth=14,
    min_samples_split=20,
    min_samples_leaf=10,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)


def apply_slippage(price, side, is_buy_action, atr=0, slippage_bps=None):
    bps_val = float(SLIPPAGE_BPS if slippage_bps is None else slippage_bps) / 10000.0
    atr_pad = float(atr or 0) * float(SLIPPAGE_ATR_FRAC)
    px = float(price)
    if is_buy_action:
        return px * (1.0 + bps_val) + atr_pad
    return px * (1.0 - bps_val) - atr_pad


@dataclass
class Trade:
    symbol: str
    side: str
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    fee: float
    reason: str
    bars_held: int = 0
    fold_id: int = 0


@dataclass
class FoldResult:
    symbol: str
    fold_id: int
    train_start: Any
    train_end: Any
    test_start: Any
    test_end: Any
    n_train: int = 0
    n_test: int = 0
    accuracy: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    final_equity: float = INITIAL_CAPITAL
    max_dd: float = 0.0
    n_signals: int = 0
    train_sec: float = 0.0
    cls_report: str = ""


def load_ohlcv(symbol: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{symbol}_USDT_1h_6y.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return pd.read_csv(path, index_col="timestamp", parse_dates=True).sort_index()


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.where(peak > 0, peak, 1.0)
    return float(dd.max() * 100.0)


def summarize_trades(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "n_trades": 0,
            "n_win": 0,
            "n_loss": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_bars_held": 0.0,
            "return_pct": 0.0,
        }
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    holds = [t.bars_held for t in trades]
    total_pnl = sum(pnls)
    return {
        "n_trades": len(trades),
        "n_win": len(wins),
        "n_loss": len(losses),
        "win_rate": len(wins) / len(trades),
        "total_pnl": total_pnl,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0),
        "avg_bars_held": float(np.mean(holds)) if holds else 0.0,
        "return_pct": total_pnl / INITIAL_CAPITAL * 100.0,
    }


def pf_str(pf: float) -> str:
    if not np.isfinite(pf):
        return "inf"
    return f"{pf:.2f}"


def simulate_fold(
    symbol: str,
    fold_id: int,
    df: pd.DataFrame,
    preds: np.ndarray,
    confs: np.ndarray,
    cooldown_bars: int = MIN_BARS_BETWEEN_TRADES,
) -> tuple[list[Trade], float, float, int]:
    """Simulate paper-like trades on one test fold (level mode)."""
    closes = df["Close"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    atrs = df["ATR"].to_numpy(dtype=float)
    adxs = df["ADX"].to_numpy(dtype=float)
    plus_di = df["+DI"].to_numpy(dtype=float)
    minus_di = df["-DI"].to_numpy(dtype=float)
    times = df.index.to_numpy()

    signals = np.empty(len(df), dtype=object)
    for i in range(len(df)):
        di_abs = abs(plus_di[i] - minus_di[i])
        if (
            adxs[i] >= ADX_STRONG_THRESHOLD
            and confs[i] >= CONFIDENCE_THRESHOLD
            and di_abs >= float(MIN_DI_DIFF)
        ):
            if preds[i] == 2 and plus_di[i] > minus_di[i]:
                signals[i] = "BUY"
            elif preds[i] == 0 and minus_di[i] > plus_di[i]:
                signals[i] = "SELL"
            else:
                signals[i] = None
        else:
            signals[i] = None

    balance = INITIAL_CAPITAL
    position = None
    trades: list[Trade] = []
    equity_curve: list[float] = []
    n_signals = 0
    last_exit_i = -10**9

    for i in range(len(df)):
        price = closes[i]
        high = highs[i]
        low = lows[i]
        atr = atrs[i]
        ts = times[i]
        signal = signals[i]

        if position is not None:
            side = position["type"]
            entry = position["entry_price"]
            amount = position["amount"]
            sl = position["sl"]
            atr_pos = position["atr"]
            entry_i = position["entry_i"]
            tp = position.get("tp")
            exit_price = None
            reason = None

            if side == "BUY":
                one_r = atr_pos * STOP_LOSS_ATR_MULT
                activate = entry + one_r * float(TRAIL_ACTIVATE_R)
                if high > position["highest_seen"]:
                    position["highest_seen"] = high
                if high >= activate:
                    position["sl"] = max(sl, high - atr_pos * TRAILING_STOP_ATR, entry)
                    sl = position["sl"]
                hit_sl = low <= sl
                hit_tp = tp is not None and high >= tp
                if hit_sl and hit_tp:
                    exit_price, reason = sl, "SL/TRAIL"
                elif hit_tp:
                    exit_price, reason = tp, "TP"
                elif hit_sl:
                    exit_price, reason = sl, "SL/TRAIL"
            else:
                one_r = atr_pos * STOP_LOSS_ATR_MULT
                activate = entry - one_r * float(TRAIL_ACTIVATE_R)
                if low < position["lowest_seen"]:
                    position["lowest_seen"] = low
                if low <= activate:
                    position["sl"] = min(sl, low + atr_pos * TRAILING_STOP_ATR, entry)
                    sl = position["sl"]
                hit_sl = high >= sl
                hit_tp = tp is not None and low <= tp
                if hit_sl and hit_tp:
                    exit_price, reason = sl, "SL/TRAIL"
                elif hit_tp:
                    exit_price, reason = tp, "TP"
                elif hit_sl:
                    exit_price, reason = sl, "SL/TRAIL"

            if exit_price is None and (i - entry_i) >= int(MAX_HOLD_HOURS):
                exit_price, reason = price, "MAX_HOLD"

            if exit_price is not None:
                exit_price = apply_slippage(
                    exit_price, side, is_buy_action=(side != "BUY"), atr=atr_pos
                )
                if side == "BUY":
                    pnl = (exit_price - entry) * amount
                else:
                    pnl = (entry - exit_price) * amount
                fee = exit_price * amount * FEE_RATE
                balance += position["margin"] + pnl - fee
                trades.append(
                    Trade(
                        symbol=symbol,
                        side=side,
                        entry_time=position["entry_time"],
                        exit_time=ts,
                        entry_price=entry,
                        exit_price=float(exit_price),
                        amount=amount,
                        pnl=pnl - fee,
                        fee=fee + position.get("entry_fee", 0.0),
                        reason=reason or "SL/TRAIL",
                        bars_held=i - entry_i,
                        fold_id=fold_id,
                    )
                )
                position = None
                last_exit_i = i

        unreal = 0.0
        margin = 0.0
        if position is not None:
            margin = position["margin"]
            if position["type"] == "BUY":
                unreal = (price - position["entry_price"]) * position["amount"]
            else:
                unreal = (position["entry_price"] - price) * position["amount"]
        equity = balance + margin + unreal
        equity_curve.append(equity)

        if position is None and signal is not None:
            n_signals += 1
            allow = True
            if cooldown_bars > 0 and (i - last_exit_i) < cooldown_bars:
                allow = False
            if allow and atr > 0 and np.isfinite(atr):
                entry_price = apply_slippage(
                    price, signal, is_buy_action=(signal == "BUY"), atr=atr
                )
                if signal == "BUY":
                    sl_price = entry_price - atr * STOP_LOSS_ATR_MULT
                    tp_price = entry_price + (entry_price - sl_price) * TAKE_PROFIT_RR
                else:
                    sl_price = entry_price + atr * STOP_LOSS_ATR_MULT
                    tp_price = entry_price - (sl_price - entry_price) * TAKE_PROFIT_RR
                price_risk = abs(entry_price - sl_price)
                if price_risk > 0:
                    risk_amount = equity * RISK_PER_TRADE_PCT
                    amount = risk_amount / price_risk
                    max_notional = equity * LEVERAGE
                    if amount * entry_price > max_notional:
                        amount = max_notional / entry_price
                    margin_req = (amount * entry_price) / LEVERAGE
                    entry_fee = entry_price * amount * FEE_RATE
                    if margin_req > 0 and amount > 0 and (margin_req + entry_fee) <= balance:
                        balance -= margin_req + entry_fee
                        position = {
                            "type": signal,
                            "entry_price": entry_price,
                            "amount": amount,
                            "margin": margin_req,
                            "atr": atr,
                            "sl": sl_price,
                            "tp": tp_price,
                            "highest_seen": entry_price,
                            "lowest_seen": entry_price,
                            "entry_time": ts,
                            "entry_i": i,
                            "entry_fee": entry_fee,
                        }

    if position is not None:
        price = closes[-1]
        entry = position["entry_price"]
        amount = position["amount"]
        side = position["type"]
        exit_price = apply_slippage(
            price, side, is_buy_action=(side != "BUY"), atr=position.get("atr", 0)
        )
        pnl = (exit_price - entry) * amount if side == "BUY" else (entry - exit_price) * amount
        fee = exit_price * amount * FEE_RATE
        balance += position["margin"] + pnl - fee
        trades.append(
            Trade(
                symbol=symbol,
                side=side,
                entry_time=position["entry_time"],
                exit_time=times[-1],
                entry_price=entry,
                exit_price=float(exit_price),
                amount=amount,
                pnl=pnl - fee,
                fee=fee + position.get("entry_fee", 0.0),
                reason="EOD",
                bars_held=len(df) - 1 - position["entry_i"],
                fold_id=fold_id,
            )
        )
        if equity_curve:
            equity_curve[-1] = balance

    eq = np.asarray(equity_curve, dtype=float) if equity_curve else np.array([INITIAL_CAPITAL])
    return trades, float(eq[-1]), max_drawdown(eq), n_signals


def make_fold_windows(
    index: pd.DatetimeIndex,
    train_days: int,
    test_days: int,
    step_days: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """Pure time-based rolling windows on the featured/labelled index."""
    t0 = index.min()
    t_max = index.max()
    windows = []
    train_td = pd.Timedelta(days=train_days)
    test_td = pd.Timedelta(days=test_days)
    step_td = pd.Timedelta(days=step_days)
    cursor = t0
    while True:
        train_start = cursor
        train_end = cursor + train_td
        test_start = train_end
        test_end = test_start + test_td
        if test_end > t_max + pd.Timedelta(hours=1):
            # allow last fold if at least half a test window remains
            if test_start >= t_max or (t_max - test_start) < pd.Timedelta(days=max(30, test_days // 2)):
                break
            test_end = t_max + pd.Timedelta(hours=1)
        windows.append((train_start, train_end, test_start, test_end))
        cursor = cursor + step_td
        if cursor + train_td >= t_max:
            break
    return windows


def run_symbol(
    symbol: str,
    train_days: int,
    test_days: int,
    step_days: int,
) -> list[FoldResult]:
    print(f"\n===== {symbol} =====")
    raw = load_ohlcv(symbol)
    print(f"[{symbol}] raw bars={len(raw)} {raw.index.min()} → {raw.index.max()}")

    df = prepare_features_v2(raw.copy())
    df = label_data_3class_quantile(df)
    # Drop rows where look-forward labels are NaN-adjacent at the very end
    # label_data already assigned; last LOOK_FORWARD rows have shifted NaN high/low
    # but regime may still be set — mask by requiring finite future via recompute check
    future_ok = df["High"].shift(-LOOK_FORWARD).notna()
    df = df.loc[future_ok].copy()
    print(f"[{symbol}] featured+labelled bars={len(df)}")

    windows = make_fold_windows(df.index, train_days, test_days, step_days)
    print(f"[{symbol}] folds={len(windows)}")

    results: list[FoldResult] = []
    for fid, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
        # Train: [tr_s, tr_e), drop last LOOK_FORWARD hours so labels don't peek into test
        train_cut = tr_e - pd.Timedelta(hours=LOOK_FORWARD + 60)  # look-forward + quantile window
        train_mask = (df.index >= tr_s) & (df.index < train_cut)
        test_mask = (df.index >= te_s) & (df.index < te_e)
        train_df = df.loc[train_mask]
        test_df = df.loc[test_mask]
        if len(train_df) < 500 or len(test_df) < 100:
            print(f"  fold {fid}: skip (train={len(train_df)} test={len(test_df)})")
            continue

        X_tr = train_df[FEATURE_COLS]
        y_tr = train_df["regime"].astype(int)
        X_te = test_df[FEATURE_COLS]
        y_te = test_df["regime"].astype(int)

        t0 = time.time()
        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(X_tr, y_tr)
        train_sec = time.time() - t0

        preds = model.predict(X_te)
        probs = model.predict_proba(X_te)
        # map class index → probability of predicted class
        classes = list(model.classes_)
        confs = np.array([probs[i, classes.index(preds[i])] for i in range(len(preds))])
        acc = float(accuracy_score(y_te, preds))
        cls_rep = classification_report(
            y_te, preds, labels=[0, 1, 2],
            target_names=["Down", "Osc", "Up"], zero_division=0,
        )

        trades, final_eq, max_dd, n_sig = simulate_fold(
            symbol, fid, test_df, preds, confs
        )
        sm = summarize_trades(trades)
        fr = FoldResult(
            symbol=symbol,
            fold_id=fid,
            train_start=train_df.index.min(),
            train_end=train_df.index.max(),
            test_start=test_df.index.min(),
            test_end=test_df.index.max(),
            n_train=len(train_df),
            n_test=len(test_df),
            accuracy=acc,
            trades=trades,
            final_equity=final_eq,
            max_dd=max_dd,
            n_signals=n_sig,
            train_sec=train_sec,
            cls_report=cls_rep,
        )
        results.append(fr)
        print(
            f"  fold {fid}: train {fr.train_start.date()}→{fr.train_end.date()} "
            f"test {fr.test_start.date()}→{fr.test_end.date()} "
            f"acc={acc:.3f} trades={sm['n_trades']} WR={sm['win_rate']*100:.1f}% "
            f"PF={pf_str(sm['profit_factor'])} ret={sm['return_pct']:+.1f}% "
            f"eq=${final_eq:,.0f} DD={max_dd:.1f}% train={train_sec:.1f}s"
        )
    return results


def write_report(
    all_results: dict[str, list[FoldResult]],
    train_days: int,
    test_days: int,
    step_days: int,
    elapsed: float,
) -> str:
    lines: list[str] = []
    lines.append("# Walk-Forward Validation v1")
    lines.append("")
    lines.append(f"- Generated (UTC): {pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Window: train **{train_days}d** / test **{test_days}d** / step **{step_days}d**")
    lines.append(
        f"- Model: RandomForest (n_estimators={RF_PARAMS['n_estimators']}, "
        f"max_depth={RF_PARAMS['max_depth']}, class_weight=balanced) — lighter than production 300/18 for runtime"
    )
    lines.append(
        f"- Features/labels: `strategy_v2_quantile.prepare_features_v2` + `label_data_3class_quantile`"
    )
    lines.append(
        f"- Gates (paper-approx): ADX≥{ADX_STRONG_THRESHOLD}, conf≥{CONFIDENCE_THRESHOLD}, "
        f"|DI|≥{MIN_DI_DIFF}, SL={STOP_LOSS_ATR_MULT} ATR, TP={TAKE_PROFIT_RR}R, "
        f"trail@{TRAIL_ACTIVATE_R}R (ATR×{TRAILING_STOP_ATR}), "
        f"slippage={SLIPPAGE_BPS}bps, fee={FEE_RATE*10000:.0f}bps, "
        f"cooldown={MIN_BARS_BETWEEN_TRADES}h, max_hold={MAX_HOLD_HOURS}h"
    )
    lines.append(f"- Per-fold starting capital: ${INITIAL_CAPITAL:,.0f} (folds independent — not chained equity)")
    lines.append(f"- Runtime: {elapsed/60:.1f} min")
    lines.append("")
    lines.append("## Limitations (read first)")
    lines.append("")
    lines.append("1. **Not live execution**: 1h bar OHLC path; same-bar SL+TP uses conservative SL-first.")
    lines.append("2. **Per-fold reset capital**: aggregate return ≠ compounded multi-year equity curve.")
    lines.append("3. **No funding / no cross-symbol portfolio constraints** (single-symbol level mode).")
    lines.append("4. **Label look-ahead truncated** on train end (−84h = look_forward 24 + quantile window 60) so train labels do not peek into the test period.")
    lines.append("5. **RF hyperparameters reduced** vs production pickle for walk-forward speed — absolute levels may differ slightly.")
    lines.append("6. **Selection bias**: this report is research evidence, not a guarantee of future paper/live PF.")
    lines.append("")

    # Aggregate across all
    all_trades: list[Trade] = []
    for sym, folds in all_results.items():
        for fr in folds:
            all_trades.extend(fr.trades)

    agg = summarize_trades(all_trades)
    lines.append("## Aggregate (all symbols × all folds)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Trades | {agg['n_trades']} |")
    lines.append(f"| Win rate | {agg['win_rate']*100:.1f}% ({agg['n_win']}/{agg['n_trades']}) |")
    lines.append(f"| Profit factor | {pf_str(agg['profit_factor'])} |")
    lines.append(f"| Sum of fold PnL | ${agg['total_pnl']:,.2f} |")
    lines.append(f"| Sum-PnL / $10k (naive) | {agg['return_pct']:+.1f}% |")
    lines.append(f"| Avg bars held | {agg['avg_bars_held']:.1f}h |")
    lines.append("")

    # Per symbol aggregate
    lines.append("## Per-symbol aggregate")
    lines.append("")
    lines.append("| Symbol | Folds | Trades | WR | PF | Sum PnL | Naive ret% | Mean fold acc | Mean fold DD% |")
    lines.append("|--------|-------|--------|----|----|---------|------------|---------------|---------------|")
    for sym, folds in all_results.items():
        tr = [t for fr in folds for t in fr.trades]
        sm = summarize_trades(tr)
        mean_acc = float(np.mean([fr.accuracy for fr in folds])) if folds else 0.0
        mean_dd = float(np.mean([fr.max_dd for fr in folds])) if folds else 0.0
        lines.append(
            f"| {sym} | {len(folds)} | {sm['n_trades']} | {sm['win_rate']*100:.1f}% | "
            f"{pf_str(sm['profit_factor'])} | ${sm['total_pnl']:,.0f} | {sm['return_pct']:+.1f}% | "
            f"{mean_acc*100:.1f}% | {mean_dd:.1f}% |"
        )
    lines.append("")

    # Per-fold tables
    for sym, folds in all_results.items():
        lines.append(f"## {sym} — per fold")
        lines.append("")
        lines.append(
            "| Fold | Train | Test | Acc | Signals | Trades | WR | PF | Final$ | Ret% | MaxDD% |"
        )
        lines.append(
            "|------|-------|------|-----|---------|--------|----|----|--------|------|--------|"
        )
        for fr in folds:
            sm = summarize_trades(fr.trades)
            ret = (fr.final_equity / INITIAL_CAPITAL - 1.0) * 100.0
            lines.append(
                f"| {fr.fold_id} | {fr.train_start.date()}→{fr.train_end.date()} | "
                f"{fr.test_start.date()}→{fr.test_end.date()} | {fr.accuracy*100:.1f}% | "
                f"{fr.n_signals} | {sm['n_trades']} | {sm['win_rate']*100:.1f}% | "
                f"{pf_str(sm['profit_factor'])} | ${fr.final_equity:,.0f} | {ret:+.1f}% | {fr.max_dd:.1f}% |"
            )
        lines.append("")

    lines.append("## Method notes")
    lines.append("")
    lines.append("- Entry: level mode (enter when flat + gated signal), mirrors `backtest_v2_offline.py`.")
    lines.append("- Classification accuracy is on 3-class regime labels (0/1/2); trading only uses gated 0/2.")
    lines.append("- Honest bar: prefer OOS PF≥1.2 with enough trades before considering real capital.")
    lines.append("")

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def parse_args():
    p = argparse.ArgumentParser(description="Walk-forward v1")
    p.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                   help="Comma-separated, e.g. BTC,ETH")
    p.add_argument("--train-days", type=int, default=365)
    p.add_argument("--test-days", type=int, default=90)
    p.add_argument("--step-days", type=int, default=90)
    return p.parse_args()


def main():
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    print(f"[*] Walk-forward v1 | symbols={symbols} "
          f"train={args.train_days}d test={args.test_days}d step={args.step_days}d")
    print(f"[*] Gates: ADX>={ADX_STRONG_THRESHOLD} conf>={CONFIDENCE_THRESHOLD} |DI|>={MIN_DI_DIFF} "
          f"SL={STOP_LOSS_ATR_MULT}ATR TP={TAKE_PROFIT_RR}R slip={SLIPPAGE_BPS}bps fee={FEE_RATE}")

    t_wall = time.time()
    all_results: dict[str, list[FoldResult]] = {}
    for sym in symbols:
        try:
            all_results[sym] = run_symbol(
                sym, args.train_days, args.test_days, args.step_days
            )
        except Exception as e:
            print(f"[!] {sym} failed: {e}")
            all_results[sym] = []
        # Soft runtime guard: if >12 min after BTC+ETH-like first symbols, still continue but warn
        elapsed = time.time() - t_wall
        if elapsed > 12 * 60:
            print(f"[!] Runtime {elapsed/60:.1f}min — continuing remaining symbols with caution")

    elapsed = time.time() - t_wall
    write_report(all_results, args.train_days, args.test_days, args.step_days, elapsed)
    print(f"\n[+] Report → {REPORT_PATH} ({elapsed/60:.1f} min)")

    # Console summary for parent
    all_trades = [t for folds in all_results.values() for fr in folds for t in fr.trades]
    agg = summarize_trades(all_trades)
    print("\n=== SUMMARY ===")
    print(f"trades={agg['n_trades']} WR={agg['win_rate']*100:.1f}% "
          f"PF={pf_str(agg['profit_factor'])} sum_pnl=${agg['total_pnl']:,.0f} "
          f"naive_ret={agg['return_pct']:+.1f}%")
    for sym, folds in all_results.items():
        tr = [t for fr in folds for t in fr.trades]
        sm = summarize_trades(tr)
        print(f"  {sym}: folds={len(folds)} trades={sm['n_trades']} "
              f"WR={sm['win_rate']*100:.1f}% PF={pf_str(sm['profit_factor'])} "
              f"ret={sm['return_pct']:+.1f}%")


if __name__ == "__main__":
    main()
