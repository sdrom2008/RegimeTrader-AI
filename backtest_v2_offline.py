#!/usr/bin/env python3
"""
Offline historical backtest for RegimeTrader-AI v2 multi model.

Mirrors paper_trader entry/exit as closely as practical:
- Features via prepare_features_v2
- Model: regime_model_v2_multi_full.pkl (fallback quantile)
- Gates: ADX + confidence + |DI|>=MIN_DI_DIFF + DI direction filter from config.py
- Long/short with ATR SL + trailing + TP (BUY high>=tp / SELL low<=tp); per-symbol cooldown
- Fee 4bps + adverse slippage (SLIPPAGE_BPS / optional ATR frac); risk sizing + leverage from config

Modes:
  level (default): enter whenever flat + gated signal (closest to paper_trader)
  edge: enter only when gated signal newly appears (reduces overtrading)

Usage:
  .venv/bin/python backtest_v2_offline.py
  .venv/bin/python backtest_v2_offline.py --mode edge --years 2
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

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
    MAX_CONCURRENT_POSITIONS,
    MAX_HOLD_HOURS,
    SLIPPAGE_BPS,
    SLIPPAGE_ATR_FRAC,
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



def apply_slippage(price, side, is_buy_action, atr=0, slippage_bps=None, slippage_atr_frac=None):
    """Adverse-only slippage on fills (mirrors paper_trader).

    side: 'BUY'/'SELL' position side (clarity for callers).
    is_buy_action: True = buy fill (open long / close short) → higher price;
                   False = sell fill (open short / close long) → lower price.
    """
    bps_val = float(SLIPPAGE_BPS if slippage_bps is None else slippage_bps) / 10000.0
    atr_frac = float(SLIPPAGE_ATR_FRAC if slippage_atr_frac is None else slippage_atr_frac)
    atr_pad = float(atr or 0) * atr_frac
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


@dataclass
class SymbolResult:
    symbol: str
    mode: str
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    final_equity: float = INITIAL_CAPITAL
    max_dd: float = 0.0
    n_bars: int = 0
    n_signals: int = 0
    start: Any = None
    end: Any = None


def _ohlcv_csv_stem(symbol: str) -> str:
    """Accept ETH or ETH/USDT (or ETH_USDT) → stem ETH_USDT for data/*.csv."""
    s = str(symbol).strip().upper().replace("/", "_")
    if s.endswith("_USDT_USDT"):
        s = s[: -len("_USDT")]
    if not s.endswith("_USDT"):
        s = f"{s}_USDT"
    return s


def load_ohlcv(symbol: str, years: Optional[float]) -> pd.DataFrame:
    stem = _ohlcv_csv_stem(symbol)
    path = os.path.join(DATA_DIR, f"{stem}_1h_6y.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"OHLCV missing for {symbol!r} → {path}")
    df = pd.read_csv(path, index_col="timestamp", parse_dates=True).sort_index()
    if years is not None and years > 0:
        cutoff = df.index.max() - pd.Timedelta(days=int(365.25 * years))
        df = df.loc[df.index >= cutoff]
    return df


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.where(peak > 0, peak, 1.0)
    return float(dd.max() * 100.0)


def simulate_symbol(
    symbol: str,
    model,
    years: Optional[float],
    mode: str = "level",
    cooldown_bars: int | None = None,
    slippage_bps: float | None = None,
) -> SymbolResult:
    if cooldown_bars is None:
        cooldown_bars = int(MIN_BARS_BETWEEN_TRADES)
    raw = load_ohlcv(symbol, years)
    df = prepare_features_v2(raw.copy())
    if df.empty:
        return SymbolResult(symbol=symbol, mode=mode)

    X = df[FEATURE_COLS]
    t0 = time.time()
    preds = model.predict(X)
    probs = model.predict_proba(X)
    confs = probs[np.arange(len(preds)), preds]
    pred_ms = (time.time() - t0) * 1000

    closes = df["Close"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    atrs = df["ATR"].to_numpy(dtype=float)
    adxs = df["ADX"].to_numpy(dtype=float)
    times = df.index.to_numpy()

    # Precompute gated signals: None / BUY / SELL
    # Align paper_trader: ADX + conf + |DI|>=MIN_DI_DIFF, then DI direction
    # (BUY only if +DI>-DI & pred==2; SELL only if -DI>+DI & pred==0)
    plus_di = df["+DI"].to_numpy(dtype=float)
    minus_di = df["-DI"].to_numpy(dtype=float)
    min_di = float(MIN_DI_DIFF)
    signals = np.empty(len(df), dtype=object)
    for i in range(len(df)):
        di_abs = abs(float(plus_di[i]) - float(minus_di[i]))
        if (
            adxs[i] >= ADX_STRONG_THRESHOLD
            and confs[i] >= CONFIDENCE_THRESHOLD
            and di_abs >= min_di
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
    prev_signal = None

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
                # Same-bar both: conservative SL (unknown path)
                if hit_sl and hit_tp:
                    exit_price = sl
                    reason = "SL/TRAIL"
                elif hit_tp:
                    exit_price = tp
                    reason = "TP"
                elif hit_sl:
                    exit_price = sl
                    reason = "SL/TRAIL"
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
                    exit_price = sl
                    reason = "SL/TRAIL"
                elif hit_tp:
                    exit_price = tp
                    reason = "TP"
                elif hit_sl:
                    exit_price = sl
                    reason = "SL/TRAIL"

            # Time stop: cut stale holds past prediction horizon
            if exit_price is None and (i - entry_i) >= int(MAX_HOLD_HOURS):
                exit_price = price
                reason = "MAX_HOLD"

            if exit_price is not None:
                # Close long = sell (adverse lower); close short = buy (adverse higher)
                exit_price = apply_slippage(
                    exit_price,
                    side,
                    is_buy_action=(side != "BUY"),
                    atr=atr_pos,
                    slippage_bps=slippage_bps,
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

        # entry
        if position is None and signal is not None:
            n_signals += 1
            allow = True
            if mode == "edge":
                allow = signal != prev_signal
            if cooldown_bars > 0 and (i - last_exit_i) < cooldown_bars:
                allow = False
            if allow and atr > 0 and np.isfinite(atr):
                entry_price = apply_slippage(
                    price,
                    signal,
                    is_buy_action=(signal == "BUY"),
                    atr=atr,
                    slippage_bps=slippage_bps,
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

        prev_signal = signal

    if position is not None:
        price = closes[-1]
        entry = position["entry_price"]
        amount = position["amount"]
        side = position["type"]
        exit_price = apply_slippage(
            price,
            side,
            is_buy_action=(side != "BUY"),
            atr=position.get("atr", 0),
            slippage_bps=slippage_bps,
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
            )
        )
        if equity_curve:
            equity_curve[-1] = balance

    eq = np.asarray(equity_curve, dtype=float) if equity_curve else np.array([INITIAL_CAPITAL])
    res = SymbolResult(
        symbol=symbol,
        mode=mode,
        trades=trades,
        equity_curve=list(eq),
        final_equity=float(eq[-1]) if len(eq) else INITIAL_CAPITAL,
        max_dd=max_drawdown(eq),
        n_bars=len(df),
        n_signals=n_signals,
        start=df.index[0],
        end=df.index[-1],
    )
    print(
        f"[{symbol}|{mode}] bars={res.n_bars} gated_hits={n_signals} trades={len(trades)} "
        f"final=${res.final_equity:,.2f} ({(res.final_equity/INITIAL_CAPITAL-1)*100:+.2f}%) "
        f"maxDD={res.max_dd:.2f}% predict={pred_ms:.0f}ms"
    )
    return res


def summarize_trades(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "n_trades": 0,
            "n_win": 0,
            "n_loss": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "total_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_bars_held": 0.0,
            "median_pnl": 0.0,
        }
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    holds = [t.bars_held for t in trades]
    return {
        "n_trades": len(trades),
        "n_win": len(wins),
        "n_loss": len(losses),
        "win_rate": len(wins) / len(trades),
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (abs(sum(losses) / len(losses)) if losses else 0.0),
        "total_pnl": sum(pnls),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "avg_bars_held": float(np.mean(holds)) if holds else 0.0,
        "median_pnl": float(np.median(pnls)),
    }


def pf_str(pf: float) -> str:
    return "inf" if not np.isfinite(pf) else f"{pf:.2f}"


def block_for_results(title: str, results: list[SymbolResult]) -> str:
    lines: list[str] = []
    lines.append(f"## {title}")
    lines.append("")
    lines.append("| 币种 | 区间 | Bars | 入场机会 | 交易数 | 胜率 | 最终权益 | 收益 | 最大回撤 | 均持仓(h) |")
    lines.append("|------|------|------|----------|--------|------|----------|------|----------|-----------|")
    all_trades: list[Trade] = []
    for r in results:
        st = summarize_trades(r.trades)
        all_trades.extend(r.trades)
        ret = (r.final_equity / INITIAL_CAPITAL - 1.0) * 100.0
        start_s = str(r.start)[:10] if r.start is not None else "-"
        end_s = str(r.end)[:10] if r.end is not None else "-"
        lines.append(
            f"| {r.symbol} | {start_s}→{end_s} | {r.n_bars} | {r.n_signals} | {st['n_trades']} | "
            f"{st['win_rate']*100:.1f}% | ${r.final_equity:,.2f} | {ret:+.2f}% | {r.max_dd:.2f}% | "
            f"{st['avg_bars_held']:.1f} |"
        )
    agg = summarize_trades(all_trades)
    total_final = sum(r.final_equity for r in results)
    total_init = INITIAL_CAPITAL * max(len(results), 1)
    total_ret = (total_final / total_init - 1.0) * 100.0
    avg_dd = float(np.mean([r.max_dd for r in results])) if results else 0.0
    worst_dd = max((r.max_dd for r in results), default=0.0)
    lines.append("")
    lines.append("| 汇总指标 | 数值 |")
    lines.append("|----------|------|")
    lines.append(f"| 初始资金合计 | ${total_init:,.2f} |")
    lines.append(f"| 最终权益合计 | ${total_final:,.2f} |")
    lines.append(f"| 总收益率 | {total_ret:+.2f}% |")
    lines.append(f"| 总交易数 | {agg['n_trades']} |")
    lines.append(f"| 胜率 | {agg['win_rate']*100:.1f}% ({agg['n_win']}W / {agg['n_loss']}L) |")
    lines.append(f"| 平均盈利 / 平均亏损 | ${agg['avg_win']:,.2f} / ${agg['avg_loss']:,.2f} |")
    lines.append(f"| 盈亏因子 | {pf_str(agg['profit_factor'])} |")
    lines.append(f"| 已实现净盈亏 | ${agg['total_pnl']:,.2f} |")
    lines.append(f"| 最大回撤 (均值 / 最差) | {avg_dd:.2f}% / {worst_dd:.2f}% |")
    lines.append(f"| 平均持仓时长 | {agg['avg_bars_held']:.1f} 小时 |")
    lines.append("")
    return "\n".join(lines), {
        "total_return_pct": total_ret,
        "total_final": total_final,
        "total_init": total_init,
        "avg_dd": avg_dd,
        "worst_dd": worst_dd,
        **agg,
        "per_symbol": [
            {
                "symbol": r.symbol,
                "final_equity": r.final_equity,
                "return_pct": (r.final_equity / INITIAL_CAPITAL - 1) * 100,
                "max_dd_pct": r.max_dd,
                **summarize_trades(r.trades),
            }
            for r in results
        ],
    }


def write_reports(
    primary: list[SymbolResult],
    sensitivity: list[SymbolResult] | None,
    model_path: str,
    years: Optional[float],
    elapsed_s: float,
    primary_mode: str,
):
    now = datetime.now(timezone.utc)
    cst = now + pd.Timedelta(hours=8)
    date_cst = cst.strftime("%Y%m%d")

    header = []
    header.append("# RegimeTrader-AI v3 Offline Backtest")
    header.append("")
    header.append(f"- **生成时间 (UTC):** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    header.append(f"- **本地时间 (CST/UTC+8):** {cst.strftime('%Y-%m-%d %H:%M:%S')}")
    header.append(f"- **模型:** `{os.path.basename(model_path)}`")
    header.append(
        f"- **门槛:** ADX≥{ADX_STRONG_THRESHOLD}, conf≥{CONFIDENCE_THRESHOLD}, "
        f"DI方向过滤, SL={STOP_LOSS_ATR_MULT}×ATR, TP={TAKE_PROFIT_RR}:1 RR, "
        f"trail={TRAILING_STOP_ATR}×ATR, cooldown={MIN_BARS_BETWEEN_TRADES} bars, "
        f"risk={RISK_PER_TRADE_PCT*100:.1f}%, lev={LEVERAGE}, "
        f"max_pos={MAX_CONCURRENT_POSITIONS}(paper), fee={FEE_RATE}, slip={SLIPPAGE_BPS}bps"
    )
    header.append(f"- **初始资金 (每币种独立):** ${INITIAL_CAPITAL:,.0f}")
    header.append(f"- **数据窗口:** {'全量 ~6y' if not years else f'最近 {years} 年'}")
    header.append(f"- **主模式:** `{primary_mode}` (对齐 paper_trader：空仓且过门槛即开仓)")
    header.append(f"- **耗时:** {elapsed_s:.1f}s")
    header.append("")

    prim_md, prim_stats = block_for_results(f"主结果（mode={primary_mode}）", primary)
    sens_md = ""
    sens_stats = None
    if sensitivity:
        sens_md, sens_stats = block_for_results("敏感性：edge 触发（信号新出现才开仓）", sensitivity)

    # Inline v1/v2/v3 snapshot for the detailed report (mirrors summary table)
    s0 = prim_stats
    cmp_md = []
    cmp_md.append("## 相对同日 v1 / v2（改进对比）")
    cmp_md.append("")
    cmp_md.append("| 指标 | v1 | v2 | v3 | v3−v2 |")
    cmp_md.append("|------|----|----|----|-------|")
    _v1r = {"n_trades": 12723, "win_rate": 0.349, "total_return_pct": -100.00, "avg_dd": 100.00, "profit_factor": 0.53, "total_pnl": -45910.69, "avg_bars_held": 6.7}
    _v2r = {"n_trades": 4870, "win_rate": 0.367, "total_return_pct": -97.94, "avg_dd": 98.19, "profit_factor": 0.63, "total_pnl": -43605.07, "avg_bars_held": 7.3}
    def _c(v, fmt):
        if fmt == "pct": return f"{v*100:.1f}%"
        if fmt == "ret": return f"{v:+.2f}%"
        if fmt == "dd": return f"{v:.2f}%"
        if fmt == "pf": return pf_str(v)
        if fmt == "money": return f"${v:,.2f}"
        if fmt == "int": return str(int(v))
        if fmt == "h": return f"{v:.1f}h"
        return str(v)
    def _d(key, fmt):
        d = s0[key] - _v2r[key]
        if fmt == "pct": return f"{d*100:+.1f}pp"
        if fmt in ("ret", "dd"): return f"{d:+.2f}pp"
        if fmt == "pf": return f"{d:+.2f}"
        if fmt == "money": return f"${d:+,.2f}"
        if fmt == "int": return f"{int(d):+d}"
        if fmt == "h": return f"{d:+.1f}h"
        return str(d)
    for lab, key, fmt in [
        ("总交易数", "n_trades", "int"), ("胜率", "win_rate", "pct"),
        ("合计收益", "total_return_pct", "ret"), ("最大回撤均值", "avg_dd", "dd"),
        ("盈亏因子", "profit_factor", "pf"), ("已实现净盈亏", "total_pnl", "money"),
        ("平均持仓", "avg_bars_held", "h"),
    ]:
        cmp_md.append(f"| {lab} | {_c(_v1r[key], fmt)} | {_c(_v2r[key], fmt)} | {_c(s0[key], fmt)} | {_d(key, fmt)} |")
    cmp_md.append("")
    cmp_md.append("**v3 改动：** risk 5%→2%，杠杆 2.5→2.0，SL 2.0→1.5×ATR，TP RR 2.0→2.5，DI方向过滤，纸交易 max 同时持仓=2。")
    cmp_md.append("")
    cmp_block = "\n".join(cmp_md) + "\n"

    limits = []
    limits.append("## 相对实盘纸交易的局限")
    limits.append("")
    limits.append("- **训练泄漏 / 过拟合风险：** 模型在含本回测区间的数据上随机划分训练，非严格 walk-forward；分类准确率乐观，但交易层仍可能亏损。")
    limits.append("- **独立账户简化：** 每币种独立 $10k，未模拟共享保证金与跨币种相关性。")
    limits.append("- **执行假设：** 收盘价入场后加不利滑点（SLIPPAGE_BPS + 可选 ATR frac）；止损按当根 High/Low 触发后再滑点；fee 按滑点后名义；无 funding / 流动性冲击。")
    limits.append("- **与 paper_trader 差异：** 纸交易扫描全市场 top-N（约 5 分钟），回测仅固定五币、按 1h K 线；宏观/新闻过滤两边均禁用。")
    limits.append("- **止盈：** 2026-09-10 起 paper + 回测均执行 TP（BUY high≥tp / SELL low≤tp）；同根同时触 TP+SL 时回测按保守 SL。")
    limits.append("- **过度交易风险：** v3 再叠加 DI 方向过滤与更低单仓风险；level 模式仍可能在趋势市外反复试错。")
    limits.append("- **组合持仓上限：** paper_trader 限制 max concurrent=2；本回测五币独立账户，无法复现跨币种持仓上限。")
    limits.append("")

    report = "\n".join(header) + cmp_block + prim_md + sens_md + "\n".join(limits)

    # Chinese-friendly summary for /workspace/backtest-summary.md
    s = prim_stats
    summary = []
    summary.append("# RegimeTrader-AI 离线回测摘要")
    summary.append("")
    summary.append(f"- 时间 (CST): {cst.strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"- 模型: `{os.path.basename(model_path)}`")
    summary.append(f"- 窗口: {'全量~6y' if not years else f'最近{years}年'} | 主模式 `{primary_mode}` | 耗时 {elapsed_s:.1f}s")
    summary.append(
        f"- 门槛: ADX≥{ADX_STRONG_THRESHOLD}, conf≥{CONFIDENCE_THRESHOLD}, "
        f"DI过滤, risk={RISK_PER_TRADE_PCT*100:.0f}%, SL={STOP_LOSS_ATR_MULT}×ATR, "
        f"TP={TAKE_PROFIT_RR}:1, cooldown={MIN_BARS_BETWEEN_TRADES}h/bars, "
        f"max_pos={MAX_CONCURRENT_POSITIONS}(paper)"
    )
    summary.append("")
    # Hard-coded prior passes (same-day offline) for v1/v2/v3 comparison
    _v1 = {
        "n_trades": 12723, "win_rate": 0.349, "total_return_pct": -100.00,
        "avg_dd": 100.00, "profit_factor": 0.53, "total_pnl": -45910.69,
        "avg_bars_held": 6.7, "total_final": 1.72,
    }
    _v2 = {
        "n_trades": 4870, "win_rate": 0.367, "total_return_pct": -97.94,
        "avg_dd": 98.19, "profit_factor": 0.63, "total_pnl": -43605.07,
        "avg_bars_held": 7.3, "total_final": 1031.52,
    }
    summary.append("## v1 / v2 / v3 对比（同日离线，五币独立账户）")
    summary.append("")
    summary.append(
        "| 指标 | v1 (ADX≥20 conf≥0.55) | v2 (ADX≥25 conf≥0.70 +TP+冷却) "
        "| v3 (risk2%+DI过滤+SL1.5/TP2.5) | v3−v2 |"
    )
    summary.append("|------|----------------------|--------------------------------|--------------------------------|--------|")

    def _fmt_cell(key, val, fmt):
        if fmt == "pct":
            return f"{val*100:.1f}%"
        if fmt == "pf":
            return pf_str(val) if isinstance(val, float) else f"{val:.2f}"
        if fmt == "money":
            return f"${val:,.2f}"
        if fmt == "ret":
            return f"{val:+.2f}%"
        if fmt == "dd":
            return f"{val:.2f}%"
        if fmt == "int":
            return f"{int(val)}"
        if fmt == "h":
            return f"{val:.1f}h"
        return str(val)

    def _delta_v3_v2(key, fmt):
        d = s[key] - _v2[key]
        if fmt == "pct":
            return f"{d*100:+.1f}pp"
        if fmt in ("ret", "dd"):
            return f"{d:+.2f}pp"
        if fmt == "pf":
            return f"{d:+.2f}"
        if fmt == "money":
            return f"${d:+,.2f}"
        if fmt == "int":
            return f"{int(d):+d}"
        if fmt == "h":
            return f"{d:+.1f}h"
        return str(d)

    rows = [
        ("总交易数", "n_trades", "int"),
        ("胜率", "win_rate", "pct"),
        ("合计收益", "total_return_pct", "ret"),
        ("最大回撤均值", "avg_dd", "dd"),
        ("盈亏因子", "profit_factor", "pf"),
        ("已实现净盈亏", "total_pnl", "money"),
        ("平均持仓", "avg_bars_held", "h"),
    ]
    for label, key, fmt in rows:
        summary.append(
            f"| {label} | {_fmt_cell(key, _v1[key], fmt)} | {_fmt_cell(key, _v2[key], fmt)} "
            f"| {_fmt_cell(key, s[key], fmt)} | {_delta_v3_v2(key, fmt)} |"
        )
    summary.append("")
    summary.append(
        "**v3 改动：** risk 5%→2%，杠杆 2.5→2.0，SL 2.0→1.5×ATR，TP RR 2.0→2.5，"
        "DI方向过滤（BUY需+DI>-DI / SELL需-DI>+DI），纸交易 max 同时持仓=2。"
    )
    summary.append("")
    summary.append("## 关键数字（主模式）")
    summary.append("")
    summary.append(f"- 总交易数: **{s['n_trades']}**")
    summary.append(f"- 胜率: **{s['win_rate']*100:.1f}%** ({s['n_win']}胜 / {s['n_loss']}负)")
    summary.append(f"- 合计收益: **{s['total_return_pct']:+.2f}%** (${s['total_init']:,.0f} → ${s['total_final']:,.2f})")
    summary.append(f"- 最大回撤 (分币种均值/最差): **{s['avg_dd']:.2f}% / {s['worst_dd']:.2f}%**")
    summary.append(f"- 盈亏因子: **{pf_str(s['profit_factor'])}** | 已实现净盈亏: **${s['total_pnl']:,.2f}**")
    summary.append(f"- 平均持仓: **{s['avg_bars_held']:.1f}h**")
    summary.append("")
    summary.append("## 分币种")
    summary.append("")
    for row in s["per_symbol"]:
        summary.append(
            f"- {row['symbol']}: 交易 {row['n_trades']}, 胜率 {row['win_rate']*100:.1f}%, "
            f"收益 {row['return_pct']:+.2f}%, 最大回撤 {row['max_dd_pct']:.2f}%"
        )
    if sens_stats:
        summary.append("")
        summary.append("## 敏感性（edge）")
        summary.append("")
        summary.append(
            f"- 交易 {sens_stats['n_trades']}, 胜率 {sens_stats['win_rate']*100:.1f}%, "
            f"收益 {sens_stats['total_return_pct']:+.2f}%, "
            f"回撤均值/最差 {sens_stats['avg_dd']:.2f}%/{sens_stats['worst_dd']:.2f}%, "
            f"盈亏因子 {pf_str(sens_stats['profit_factor'])}"
        )
    summary.append("")
    summary.append("## 局限（相对 live paper）")
    summary.append("")
    summary.append("- 模型训练含同区间数据 → 非严格 walk-forward")
    summary.append("- 五币种独立账户；收盘入场 + HL 止损；无滑点/funding；非 top-N 扫描")
    summary.append("- level 模式对齐纸交易；v3：TP+冷却+更高门槛 + DI方向过滤 + 更低仓位风险；max_pos=2 仅纸交易组合层（回测每币独立最多1仓）")
    summary.append("- 未停止 live_executor 纸交易进程")
    summary.append("")

    reports_dir = os.path.join(REPO_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, f"backtest_{date_cst}_v3.md")
    summary_path = "/workspace/backtest-summary.md"
    stats_path = os.path.join(reports_dir, f"backtest_{date_cst}_v3.json")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model": os.path.basename(model_path),
                "years": years,
                "elapsed_s": elapsed_s,
                "primary_mode": primary_mode,
                "primary": prim_stats,
                "edge_sensitivity": sens_stats,
            },
            f,
            indent=2,
            default=str,
        )

    print("\n" + "\n".join(summary))
    print(f"[+] Report: {report_path}")
    print(f"[+] Summary: {summary_path}")
    print(f"[+] Stats JSON: {stats_path}")


def write_slippage_v4_report(
    with_slip: list[SymbolResult],
    no_slip: list[SymbolResult],
    model_path: str,
    years: Optional[float],
    slip_bps: float,
    elapsed_s: float,
):
    """Short STRATEGY_V4 slippage vs no-slip comparison report."""
    now = datetime.now(timezone.utc)
    cst = now + pd.Timedelta(hours=8)
    _, s_slip = block_for_results("with_slip", with_slip)
    _, s_nos = block_for_results("no_slip", no_slip)

    lines = []
    lines.append("# RegimeTrader-AI STRATEGY_V4 — Slippage Backtest")
    lines.append("")
    lines.append(f"- **生成时间 (UTC):** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **本地时间 (CST/UTC+8):** {cst.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **模型:** `{os.path.basename(model_path)}`")
    lines.append(
        f"- **门槛:** ADX≥{ADX_STRONG_THRESHOLD}, conf≥{CONFIDENCE_THRESHOLD}, DI过滤, "
        f"risk={RISK_PER_TRADE_PCT*100:.0f}%, lev={LEVERAGE}, SL={STOP_LOSS_ATR_MULT}×ATR, "
        f"TP={TAKE_PROFIT_RR}:1, trail={TRAILING_STOP_ATR}, max_pos={MAX_CONCURRENT_POSITIONS}, "
        f"cooldown={MIN_BARS_BETWEEN_TRADES}h, max_hold={MAX_HOLD_HOURS}h"
    )
    lines.append(
        f"- **费用:** fee={FEE_RATE} on slipped notional; SLIPPAGE_ATR_FRAC={SLIPPAGE_ATR_FRAC}"
    )
    lines.append(
        f"- **窗口:** {'全量~6y' if not years else f'最近 {years} 年'} | mode=level | 耗时 {elapsed_s:.1f}s"
    )
    lines.append("")
    lines.append("## 有滑点 vs 无滑点（同配置）")
    lines.append("")
    lines.append(f"| 指标 | 无滑点 (0 bps) | 有滑点 ({slip_bps:.1f} bps) | Δ |")
    lines.append("|------|----------------|---------------------|---|")

    def row(label, key, fmt):
        a, b = s_nos[key], s_slip[key]
        d = b - a
        if fmt == "pct":
            return f"| {label} | {a*100:.1f}% | {b*100:.1f}% | {(d)*100:+.1f}pp |"
        if fmt == "ret":
            return f"| {label} | {a:+.2f}% | {b:+.2f}% | {d:+.2f}pp |"
        if fmt == "dd":
            return f"| {label} | {a:.2f}% | {b:.2f}% | {d:+.2f}pp |"
        if fmt == "pf":
            return f"| {label} | {pf_str(a)} | {pf_str(b)} | {d:+.3f} |"
        if fmt == "money":
            return f"| {label} | ${a:,.2f} | ${b:,.2f} | ${d:+,.2f} |"
        if fmt == "int":
            return f"| {label} | {int(a)} | {int(b)} | {int(d):+d} |"
        if fmt == "h":
            return f"| {label} | {a:.1f}h | {b:.1f}h | {d:+.1f}h |"
        return f"| {label} | {a} | {b} | {d} |"

    for lab, key, fmt in [
        ("总交易数", "n_trades", "int"),
        ("胜率", "win_rate", "pct"),
        ("合计收益", "total_return_pct", "ret"),
        ("最大回撤均值", "avg_dd", "dd"),
        ("盈亏因子", "profit_factor", "pf"),
        ("已实现净盈亏", "total_pnl", "money"),
        ("平均持仓", "avg_bars_held", "h"),
        ("最终权益合计", "total_final", "money"),
    ]:
        lines.append(row(lab, key, fmt))
    lines.append("")
    lines.append("## 分币种最终权益")
    lines.append("")
    lines.append("| 币种 | 无滑点权益 | 有滑点权益 | Δ权益 | 无滑点收益 | 有滑点收益 |")
    lines.append("|------|------------|------------|--------|------------|------------|")
    nos_map = {r["symbol"]: r for r in s_nos["per_symbol"]}
    for r in s_slip["per_symbol"]:
        n = nos_map.get(r["symbol"], {})
        nf = float(n.get("final_equity", 0))
        sf = float(r["final_equity"])
        nr = float(n.get("return_pct", 0))
        sr = float(r["return_pct"])
        lines.append(
            f"| {r['symbol']} | ${nf:,.2f} | ${sf:,.2f} | ${sf-nf:+,.2f} | {nr:+.2f}% | {sr:+.2f}% |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append(
        f"- 滑点规则：开多/平空买高、开空/平多卖低，各 {slip_bps} bps；"
        "TP/SL/MAX_HOLD/EOD 理想价均再滑不利方向；fee 按滑点后名义计。"
    )
    lines.append(
        "- 与 STRATEGY_V4 纸交易一致：训练集五币、conf≥0.80、ADX≥25、DI 过滤、risk2%/lev2、max_pos=1。"
    )
    lines.append("- 回测仍为每币独立 $10k；未模拟共享保证金。训练泄漏等局限同既有离线回测。")
    lines.append("")

    out = os.path.join(REPO_ROOT, "reports", "backtest_slippage_v4.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[+] Slippage compare report: {out}")


def run_batch(model, symbols, years, mode, cooldown_bars, slippage_bps=None) -> list[SymbolResult]:
    out = []
    for sym in symbols:
        out.append(
            simulate_symbol(
                sym, model, years, mode=mode, cooldown_bars=cooldown_bars,
                slippage_bps=slippage_bps,
            )
        )
    return out


def main():
    parser = argparse.ArgumentParser(description="RegimeTrader-AI v2 offline backtest")
    parser.add_argument("--years", type=float, default=None, help="Use last N years only")
    parser.add_argument("--symbols", nargs="*", default=SYMBOLS)
    parser.add_argument("--mode", choices=["level", "edge"], default="level")
    parser.add_argument("--cooldown", type=int, default=None, help="Bars to wait after exit (default: MIN_BARS_BETWEEN_TRADES from config)")
    parser.add_argument("--with-edge", action="store_true", help="Also run edge sensitivity")
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=None,
        help="Override SLIPPAGE_BPS (default: config). Use 0 for no-slip comparison.",
    )
    parser.add_argument(
        "--compare-slippage",
        action="store_true",
        help="Also run zero-slippage pass and write reports/backtest_slippage_v4.md",
    )
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    t_start = time.time()
    model_path = resolve_model_file()
    print(f"[*] Loading model: {model_path}")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    cd = args.cooldown if args.cooldown is not None else MIN_BARS_BETWEEN_TRADES
    slip = args.slippage_bps if args.slippage_bps is not None else float(SLIPPAGE_BPS)
    print(
        f"[*] Gates: ADX>={ADX_STRONG_THRESHOLD} conf>={CONFIDENCE_THRESHOLD} "
        f"|DI|>={MIN_DI_DIFF} DI-dir TP=on cooldown={cd}bars risk={RISK_PER_TRADE_PCT} "
        f"SL={STOP_LOSS_ATR_MULT} TP_RR={TAKE_PROFIT_RR} slip={slip}bps"
    )
    print(f"[*] Symbols: {args.symbols} | years={args.years or 'full'} | mode={args.mode}")

    primary = run_batch(
        model, args.symbols, args.years, args.mode, args.cooldown, slippage_bps=slip
    )
    sensitivity = None
    if args.with_edge and args.mode != "edge":
        print("[*] Running edge sensitivity pass...")
        sensitivity = run_batch(
            model, args.symbols, args.years, "edge", args.cooldown, slippage_bps=slip
        )

    elapsed = time.time() - t_start
    write_reports(primary, sensitivity, model_path, args.years, elapsed, args.mode)

    if args.compare_slippage:
        print("[*] Running no-slippage comparison pass...")
        t1 = time.time()
        no_slip = run_batch(
            model, args.symbols, args.years, args.mode, args.cooldown, slippage_bps=0.0
        )
        write_slippage_v4_report(primary, no_slip, model_path, args.years, slip, time.time() - t_start)
        print(f"[*] Compare slip elapsed total: {time.time() - t_start:.1f}s (compare pass {time.time()-t1:.1f}s)")

    print(f"[*] Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
