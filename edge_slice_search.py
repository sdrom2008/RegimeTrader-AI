#!/usr/bin/env python3
"""
Edge slice search: find gated trend subsets with PF>=1.2 after fee 4bps + slip 2bps.

Uses existing multi_full model + strategy_v2_quantile features on last N years.
Does NOT touch live_executor / git push.
"""
from __future__ import annotations

import os
import pickle
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd

from config import (
    LEVERAGE,
    RISK_PER_TRADE_PCT,
    STOP_LOSS_ATR_MULT,
    TAKE_PROFIT_RR,
    TRAILING_STOP_ATR,
    TRAIL_ACTIVATE_R,
    MIN_BARS_BETWEEN_TRADES,
    MAX_HOLD_HOURS,
    SLIPPAGE_BPS,
    resolve_model_file,
)
from strategy_v2_quantile import prepare_features_v2

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
INITIAL_CAPITAL = 10_000.0
FEE_RATE = 0.0004

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

CONF_GRID = [0.80, 0.85, 0.90]
ADX_GRID = [25, 30, 35]
DI_DIFF_GRID = [0.0, 5.0, 10.0, 15.0]  # |DI_diff| min; 0 = off
SIDE_GRID = ["both", "long", "short"]


def apply_slippage(price, is_buy_action, atr=0, slippage_bps=None):
    bps_val = float(SLIPPAGE_BPS if slippage_bps is None else slippage_bps) / 10000.0
    px = float(price)
    atr_pad = 0.0
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
    r_multiple: float = 0.0


@dataclass
class PreparedSymbol:
    symbol: str
    times: np.ndarray
    closes: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    atrs: np.ndarray
    adxs: np.ndarray
    plus_di: np.ndarray
    minus_di: np.ndarray
    di_diff_abs: np.ndarray
    preds: np.ndarray
    confs: np.ndarray
    start: Any
    end: Any


def load_ohlcv(symbol: str, years: float) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{symbol}_USDT_1h_6y.csv")
    df = pd.read_csv(path, index_col="timestamp", parse_dates=True).sort_index()
    cutoff = df.index.max() - pd.Timedelta(days=int(365.25 * years))
    return df.loc[df.index >= cutoff]


def prepare_all(model, years: float = 2.0) -> list[PreparedSymbol]:
    out: list[PreparedSymbol] = []
    for sym in SYMBOLS:
        raw = load_ohlcv(sym, years)
        df = prepare_features_v2(raw.copy())
        if df.empty:
            continue
        X = df[FEATURE_COLS]
        t0 = time.time()
        preds = model.predict(X)
        probs = model.predict_proba(X)
        confs = probs[np.arange(len(preds)), preds]
        print(f"[prep {sym}] bars={len(df)} predict={(time.time()-t0)*1000:.0f}ms "
              f"{df.index[0].date()}→{df.index[-1].date()}")
        out.append(
            PreparedSymbol(
                symbol=sym,
                times=df.index.to_numpy(),
                closes=df["Close"].to_numpy(dtype=float),
                highs=df["High"].to_numpy(dtype=float),
                lows=df["Low"].to_numpy(dtype=float),
                atrs=df["ATR"].to_numpy(dtype=float),
                adxs=df["ADX"].to_numpy(dtype=float),
                plus_di=df["+DI"].to_numpy(dtype=float),
                minus_di=df["-DI"].to_numpy(dtype=float),
                di_diff_abs=np.abs(df["DI_diff"].to_numpy(dtype=float)),
                preds=np.asarray(preds),
                confs=np.asarray(confs, dtype=float),
                start=df.index[0],
                end=df.index[-1],
            )
        )
    return out


def build_signals(
    p: PreparedSymbol,
    conf_min: float,
    adx_min: float,
    di_diff_min: float,
    side_mode: str,
) -> np.ndarray:
    n = len(p.closes)
    signals = np.empty(n, dtype=object)
    signals[:] = None
    for i in range(n):
        if p.adxs[i] < adx_min or p.confs[i] < conf_min:
            continue
        if p.di_diff_abs[i] < di_diff_min:
            continue
        if p.preds[i] == 2 and p.plus_di[i] > p.minus_di[i]:
            if side_mode in ("both", "long"):
                signals[i] = "BUY"
        elif p.preds[i] == 0 and p.minus_di[i] > p.plus_di[i]:
            if side_mode in ("both", "short"):
                signals[i] = "SELL"
    return signals


def simulate(
    p: PreparedSymbol,
    signals: np.ndarray,
    *,
    trail_on: bool = True,
    cooldown_bars: int = MIN_BARS_BETWEEN_TRADES,
    slippage_bps: float = SLIPPAGE_BPS,
) -> list[Trade]:
    balance = INITIAL_CAPITAL
    position = None
    trades: list[Trade] = []
    last_exit_i = -10**9
    trail_atr = float(TRAILING_STOP_ATR) if trail_on else 0.0
    trail_act = float(TRAIL_ACTIVATE_R) if trail_on else 1e9  # never activate if off

    for i in range(len(p.closes)):
        price = p.closes[i]
        high = p.highs[i]
        low = p.lows[i]
        atr = p.atrs[i]
        ts = p.times[i]
        signal = signals[i]

        if position is not None:
            side = position["type"]
            entry = position["entry_price"]
            amount = position["amount"]
            sl = position["sl"]
            atr_pos = position["atr"]
            entry_i = position["entry_i"]
            tp = position.get("tp")
            one_r = atr_pos * STOP_LOSS_ATR_MULT
            exit_price = None
            reason = None

            if side == "BUY":
                activate = entry + one_r * trail_act
                if high > position["highest_seen"]:
                    position["highest_seen"] = high
                if trail_on and high >= activate:
                    position["sl"] = max(sl, high - atr_pos * trail_atr, entry)
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
                activate = entry - one_r * trail_act
                if low < position["lowest_seen"]:
                    position["lowest_seen"] = low
                if trail_on and low <= activate:
                    position["sl"] = min(sl, low + atr_pos * trail_atr, entry)
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
                    exit_price, is_buy_action=(side != "BUY"), atr=atr_pos, slippage_bps=slippage_bps
                )
                if side == "BUY":
                    pnl = (exit_price - entry) * amount
                else:
                    pnl = (entry - exit_price) * amount
                fee = exit_price * amount * FEE_RATE
                net = pnl - fee
                balance += position["margin"] + net
                r_mult = net / (amount * one_r) if (amount * one_r) > 0 else 0.0
                trades.append(
                    Trade(
                        symbol=p.symbol,
                        side=side,
                        entry_time=position["entry_time"],
                        exit_time=ts,
                        entry_price=entry,
                        exit_price=float(exit_price),
                        amount=amount,
                        pnl=net,
                        fee=fee + position.get("entry_fee", 0.0),
                        reason=reason or "SL/TRAIL",
                        bars_held=i - entry_i,
                        r_multiple=float(r_mult),
                    )
                )
                position = None
                last_exit_i = i

        # mark-to-market equity for sizing
        unreal = 0.0
        margin = 0.0
        if position is not None:
            margin = position["margin"]
            if position["type"] == "BUY":
                unreal = (price - position["entry_price"]) * position["amount"]
            else:
                unreal = (position["entry_price"] - price) * position["amount"]
        equity = balance + margin + unreal

        if position is None and signal is not None:
            if cooldown_bars > 0 and (i - last_exit_i) < cooldown_bars:
                continue
            if atr <= 0 or not np.isfinite(atr):
                continue
            entry_price = apply_slippage(
                price, is_buy_action=(signal == "BUY"), atr=atr, slippage_bps=slippage_bps
            )
            if signal == "BUY":
                sl_price = entry_price - atr * STOP_LOSS_ATR_MULT
                tp_price = entry_price + (entry_price - sl_price) * TAKE_PROFIT_RR
            else:
                sl_price = entry_price + atr * STOP_LOSS_ATR_MULT
                tp_price = entry_price - (sl_price - entry_price) * TAKE_PROFIT_RR
            price_risk = abs(entry_price - sl_price)
            if price_risk <= 0:
                continue
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
        price = p.closes[-1]
        entry = position["entry_price"]
        amount = position["amount"]
        side = position["type"]
        atr_pos = position.get("atr", 0)
        one_r = atr_pos * STOP_LOSS_ATR_MULT
        exit_price = apply_slippage(price, is_buy_action=(side != "BUY"), atr=atr_pos)
        pnl = (exit_price - entry) * amount if side == "BUY" else (entry - exit_price) * amount
        fee = exit_price * amount * FEE_RATE
        net = pnl - fee
        r_mult = net / (amount * one_r) if (amount * one_r) > 0 else 0.0
        trades.append(
            Trade(
                symbol=p.symbol,
                side=side,
                entry_time=position["entry_time"],
                exit_time=p.times[-1],
                entry_price=entry,
                exit_price=float(exit_price),
                amount=amount,
                pnl=net,
                fee=fee + position.get("entry_fee", 0.0),
                reason="EOD",
                bars_held=len(p.closes) - 1 - position["entry_i"],
                r_multiple=float(r_mult),
            )
        )
    return trades


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return dict(
            n_trades=0, n_win=0, n_loss=0, win_rate=0.0, profit_factor=0.0,
            total_pnl=0.0, avg_r=0.0, avg_bars=0.0, gross_win=0.0, gross_loss=0.0,
        )
    pnls = np.array([t.pnl for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gw = float(wins.sum()) if len(wins) else 0.0
    gl = float(abs(losses.sum())) if len(losses) else 0.0
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    return dict(
        n_trades=len(trades),
        n_win=int(len(wins)),
        n_loss=int(len(losses)),
        win_rate=float(len(wins) / len(trades)),
        profit_factor=float(pf),
        total_pnl=float(pnls.sum()),
        avg_r=float(np.mean([t.r_multiple for t in trades])),
        avg_bars=float(np.mean([t.bars_held for t in trades])),
        gross_win=gw,
        gross_loss=gl,
    )


def pf_str(pf: float) -> str:
    if not np.isfinite(pf):
        return "inf"
    return f"{pf:.2f}"


def run_slice(prepared: list[PreparedSymbol], conf, adx, di_min, side, trail_on=True) -> dict:
    all_trades: list[Trade] = []
    for p in prepared:
        sigs = build_signals(p, conf, adx, di_min, side)
        all_trades.extend(simulate(p, sigs, trail_on=trail_on))
    st = summarize(all_trades)
    st.update(
        conf=conf,
        adx=adx,
        di_diff_min=di_min,
        side=side,
        trail_on=trail_on,
        n_long=sum(1 for t in all_trades if t.side == "BUY"),
        n_short=sum(1 for t in all_trades if t.side == "SELL"),
    )
    # per-symbol quick
    by_sym = {}
    for p in prepared:
        sym_tr = [t for t in all_trades if t.symbol == p.symbol]
        by_sym[p.symbol] = summarize(sym_tr)
    st["by_symbol"] = by_sym
    return st


def main():
    years = 2.0
    t_wall = time.time()
    model_path = resolve_model_file()
    print(f"Loading model: {model_path}")
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    prepared = prepare_all(model, years=years)
    if not prepared:
        raise SystemExit("No prepared symbols")

    rows = []
    total = len(CONF_GRID) * len(ADX_GRID) * len(DI_DIFF_GRID) * len(SIDE_GRID)
    done = 0
    for conf in CONF_GRID:
        for adx in ADX_GRID:
            for di_min in DI_DIFF_GRID:
                for side in SIDE_GRID:
                    done += 1
                    st = run_slice(prepared, conf, adx, di_min, side, trail_on=True)
                    rows.append(st)
                    if done % 18 == 0 or done == total:
                        print(f"  sweep {done}/{total} last PF={pf_str(st['profit_factor'])} "
                              f"n={st['n_trades']} conf={conf} adx={adx} |DI|>={di_min} {side}")

    # rank
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            -r["profit_factor"] if np.isfinite(r["profit_factor"]) else -999,
            -r["n_trades"],
            -r["avg_r"],
        ),
    )
    hits = [r for r in rows_sorted if r["n_trades"] >= 20 and r["profit_factor"] >= 1.2]
    near = [r for r in rows_sorted if r["n_trades"] >= 15 and r["profit_factor"] >= 1.0]

    # baseline (current paper gates)
    base = run_slice(prepared, 0.80, 25, 0.0, "both", trail_on=True)

    # exit variant on best interesting slice
    # prefer PF>=1.2 with most trades; else best PF with n>=20; else overall best with n>=10
    candidates = [r for r in rows_sorted if r["n_trades"] >= 20]
    if hits:
        best = max(hits, key=lambda r: (r["n_trades"], r["profit_factor"]))
    elif candidates:
        best = candidates[0]
    else:
        best = next((r for r in rows_sorted if r["n_trades"] >= 10), rows_sorted[0])

    best_on = run_slice(
        prepared, best["conf"], best["adx"], best["di_diff_min"], best["side"], trail_on=True
    )
    best_off = run_slice(
        prepared, best["conf"], best["adx"], best["di_diff_min"], best["side"], trail_on=False
    )

    # Shanghai time label
    now_utc = datetime.now(timezone.utc)
    now_cst = now_utc + timedelta(hours=8)
    start_s = str(prepared[0].start)[:10]
    end_s = str(prepared[0].end)[:10]

    def row_line(r):
        return (
            f"| {r['conf']:.2f} | {r['adx']} | {r['di_diff_min']:.0f} | {r['side']} | "
            f"{r['n_trades']} | {r['win_rate']*100:.1f}% | {pf_str(r['profit_factor'])} | "
            f"{r['avg_r']:+.2f}R | ${r['total_pnl']:,.0f} | L{r['n_long']}/S{r['n_short']} |"
        )

    lines = []
    lines.append("# Edge Slice Search — gated trend PF≥1.2")
    lines.append("")
    lines.append(f"- Generated (CST/UTC+8): {now_cst.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Model: `{os.path.basename(model_path)}`")
    lines.append(f"- Features: `strategy_v2_quantile.prepare_features_v2`")
    lines.append(f"- Window: last **{years:.0f}y** 1h ({start_s}→{end_s}), 5 symbols independent $10k")
    lines.append(
        "- Costs: fee **4bps** + slippage **2bps** (adverse); SL=1.5 ATR, TP=2.5R, "
        "cooldown=6h, max_hold=24h, trail@1R (default ON in sweep)"
    )
    lines.append(
        f"- Grid: conf={CONF_GRID}, ADX={ADX_GRID}, |DI_diff|min={DI_DIFF_GRID}, "
        f"side={SIDE_GRID} → **{total}** slices"
    )
    lines.append(f"- Runtime: {(time.time()-t_wall)/60:.1f} min")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("1. Fixed multi_full model on last-2y bars — **not** strict walk-forward OOS (train overlap possible).")
    lines.append("2. Per-symbol independent accounts; no portfolio max_pos / funding.")
    lines.append("3. Selection bias: PF≥1.2 slices are mined from the same window — treat as hypothesis for paper, not edge proof.")
    lines.append("4. Same-bar SL+TP uses conservative SL-first.")
    lines.append("")
    lines.append("## Baseline (paper-like: conf≥0.80, ADX≥25, |DI|≥0, both, trail ON)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Trades | {base['n_trades']} |")
    lines.append(f"| WR | {base['win_rate']*100:.1f}% ({base['n_win']}W/{base['n_loss']}L) |")
    lines.append(f"| PF | {pf_str(base['profit_factor'])} |")
    lines.append(f"| Avg R | {base['avg_r']:+.2f}R |")
    lines.append(f"| Net PnL | ${base['total_pnl']:,.2f} |")
    lines.append("")
    lines.append("## Hits: PF≥1.2 and n≥20")
    lines.append("")
    if not hits:
        lines.append("**None.** No slice in this grid cleared PF≥1.2 with ≥20 trades.")
        lines.append("")
    else:
        lines.append("| Conf | ADX | \|DI\|≥ | Side | Trades | WR | PF | Avg R | Net PnL | L/S |")
        lines.append("|------|-----|--------|------|--------|----|----|-------|---------|-----|")
        for r in hits[:30]:
            lines.append(row_line(r))
        lines.append("")

    lines.append("## Near-misses: PF≥1.0 and n≥15 (top 25 by PF)")
    lines.append("")
    lines.append("| Conf | ADX | \|DI\|≥ | Side | Trades | WR | PF | Avg R | Net PnL | L/S |")
    lines.append("|------|-----|--------|------|--------|----|----|-------|---------|-----|")
    for r in near[:25]:
        lines.append(row_line(r))
    lines.append("")

    lines.append("## Top 15 overall (by PF, then n)")
    lines.append("")
    lines.append("| Conf | ADX | \|DI\|≥ | Side | Trades | WR | PF | Avg R | Net PnL | L/S |")
    lines.append("|------|-----|--------|------|--------|----|----|-------|---------|-----|")
    for r in rows_sorted[:15]:
        lines.append(row_line(r))
    lines.append("")

    # Best slice detail + trail A/B
    lines.append("## Best slice (for exit A/B)")
    lines.append("")
    lines.append(
        f"- Selected: conf≥**{best['conf']:.2f}**, ADX≥**{best['adx']}**, "
        f"|DI_diff|≥**{best['di_diff_min']:.0f}**, side=**{best['side']}**"
    )
    lines.append("")
    lines.append("| Variant | Trades | WR | PF | Avg R | Net PnL | Avg hold (h) |")
    lines.append("|---------|--------|----|----|-------|---------|--------------|")
    for label, r in [("trail@1R ON", best_on), ("trail OFF (fixed SL+TP)", best_off)]:
        lines.append(
            f"| {label} | {r['n_trades']} | {r['win_rate']*100:.1f}% | {pf_str(r['profit_factor'])} | "
            f"{r['avg_r']:+.2f}R | ${r['total_pnl']:,.0f} | {r['avg_bars']:.1f} |"
        )
    lines.append("")
    lines.append("### Per-symbol (best slice, trail ON)")
    lines.append("")
    lines.append("| Symbol | Trades | WR | PF | Avg R | Net PnL |")
    lines.append("|--------|--------|----|----|-------|---------|")
    for sym, sm in best_on["by_symbol"].items():
        lines.append(
            f"| {sym} | {sm['n_trades']} | {sm['win_rate']*100:.1f}% | {pf_str(sm['profit_factor'])} | "
            f"{sm['avg_r']:+.2f}R | ${sm['total_pnl']:,.0f} |"
        )
    lines.append("")

    # Sparse high-conf note
    sparse = [r for r in rows_sorted if r["conf"] >= 0.90 and r["adx"] >= 30]
    lines.append("## High-bar sparse slices (conf≥0.90 & ADX≥30)")
    lines.append("")
    lines.append("| Conf | ADX | \|DI\|≥ | Side | Trades | WR | PF | Avg R | Net PnL | L/S |")
    lines.append("|------|-----|--------|------|--------|----|----|-------|---------|-----|")
    for r in sparse[:20]:
        lines.append(row_line(r))
    lines.append("")

    lines.append("## Takeaways")
    lines.append("")
    if hits:
        lines.append(
            f"- **{len(hits)}** slice(s) hit PF≥1.2 with n≥20 under fee+slip — candidate for tighter paper gates."
        )
    else:
        top = rows_sorted[0]
        lines.append(
            f"- **No PF≥1.2 / n≥20 hit.** Best: conf≥{top['conf']:.2f} ADX≥{top['adx']} "
            f"|DI|≥{top['di_diff_min']:.0f} {top['side']} → PF={pf_str(top['profit_factor'])}, "
            f"n={top['n_trades']}, WR={top['win_rate']*100:.1f}%, avgR={top['avg_r']:+.2f}."
        )
    delta_pf = best_on["profit_factor"] - best_off["profit_factor"]
    lines.append(
        f"- Trail@1R vs off on best slice: PF {pf_str(best_on['profit_factor'])} vs "
        f"{pf_str(best_off['profit_factor'])} (Δ={delta_pf:+.2f}); "
        f"avgR {best_on['avg_r']:+.2f} vs {best_off['avg_r']:+.2f}."
    )
    lines.append(
        f"- Paper baseline PF={pf_str(base['profit_factor'])} (n={base['n_trades']}) — "
        "raising conf/ADX/|DI| generally cuts trades; watch sample size before promoting a slice."
    )
    lines.append("- Next: validate any PF≥1.2 candidate on walk-forward OOS folds before changing live paper gates.")
    lines.append("")

    report_path = os.path.join(REPO_ROOT, "reports", "edge_slice_search.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {report_path}")

    # compact summary for parent / workspace root
    summary = []
    summary.append("# Edge slice search summary")
    summary.append("")
    summary.append(f"- CST: {now_cst.strftime('%Y-%m-%d %H:%M')} | window last {years:.0f}y | model multi_full | fee4bps+slip2bps")
    summary.append(f"- Baseline paper gates: n={base['n_trades']} WR={base['win_rate']*100:.1f}% PF={pf_str(base['profit_factor'])} avgR={base['avg_r']:+.2f}")
    if hits:
        summary.append(f"- **Hits PF≥1.2 (n≥20): {len(hits)}**")
        for r in hits[:8]:
            summary.append(
                f"  - conf≥{r['conf']:.2f} ADX≥{r['adx']} |DI|≥{r['di_diff_min']:.0f} {r['side']}: "
                f"n={r['n_trades']} WR={r['win_rate']*100:.1f}% PF={pf_str(r['profit_factor'])} avgR={r['avg_r']:+.2f}"
            )
    else:
        summary.append("- **No PF≥1.2 with n≥20**")
        summary.append("- Near-misses / best:")
        for r in near[:5] if near else rows_sorted[:5]:
            summary.append(
                f"  - conf≥{r['conf']:.2f} ADX≥{r['adx']} |DI|≥{r['di_diff_min']:.0f} {r['side']}: "
                f"n={r['n_trades']} WR={r['win_rate']*100:.1f}% PF={pf_str(r['profit_factor'])} avgR={r['avg_r']:+.2f}"
            )
    summary.append(
        f"- Best-slice trail ON vs OFF: PF {pf_str(best_on['profit_factor'])} / {pf_str(best_off['profit_factor'])} "
        f"(conf≥{best['conf']:.2f} ADX≥{best['adx']} |DI|≥{best['di_diff_min']:.0f} {best['side']})"
    )
    summary.append("- Full table: `RegimeTrader-AI/reports/edge_slice_search.md`")
    summary.append("- live_executor left running; no git push")
    summary.append("")

    summary_path = "/workspace/edge-slice-summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    print(f"Wrote {summary_path}")

    # also dump CSV for reuse
    flat = []
    for r in rows_sorted:
        flat.append({
            "conf": r["conf"], "adx": r["adx"], "di_diff_min": r["di_diff_min"],
            "side": r["side"], "n_trades": r["n_trades"], "win_rate": r["win_rate"],
            "profit_factor": r["profit_factor"] if np.isfinite(r["profit_factor"]) else None,
            "avg_r": r["avg_r"], "total_pnl": r["total_pnl"],
            "n_long": r["n_long"], "n_short": r["n_short"],
        })
    csv_path = os.path.join(REPO_ROOT, "reports", "edge_slice_search.csv")
    pd.DataFrame(flat).to_csv(csv_path, index=False)
    print(f"Wrote {csv_path}")
    print(f"DONE hits={len(hits)} near={len(near)} best_pf={pf_str(best_on['profit_factor'])}")


if __name__ == "__main__":
    main()
