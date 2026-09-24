#!/usr/bin/env python3
"""
Export daily gate-reject summary from logs/signal_journal.jsonl.

Writes reports/gate_rejects_daily.csv (idempotent upsert by date: full rebuild
from journal each run is safe and overwrites same-day rows).

口径（与 evaluate_signal_journal / 日报 choke 一致）:
  - 去重: (symbol, closed_1h_bar)；缺 closed_1h_bar 时用 timestamp 截到整点
  - 白名单: config.TRADING_SYMBOLS（空则不过滤）
  - 有序拒因: ADX → conf → |DI|（同 paper_trader gate_stats）
  - PASS / fail_* 仅计有方向 bar（pred in {0,2} / Up/Down）
  - no_dir = Osc/HOLD（pred==1）
  - dir_rejected = 有方向但未 PASS
  - scan_total = 当日全部 uniq bars（含无方向）

不改 live 门槛；只读 journal。用法:

  python scripts/export_gate_rejects_daily.py
  python scripts/export_gate_rejects_daily.py --journal logs/signal_journal.jsonl
  python scripts/export_gate_rejects_daily.py --out reports/gate_rejects_daily.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

from config import (  # noqa: E402
    ADX_STRONG_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    MIN_DI_DIFF,
    SIGNAL_JOURNAL_FILE,
    TRADING_SYMBOLS,
)

CSV_COLUMNS = [
    "date",
    "scan_total",
    "no_dir",
    "dir_total",
    "PASS",
    "fail_adx",
    "fail_conf",
    "fail_di",
    "dir_rejected",
    "near_max_adx",
    "near_max_conf",
    "near_max_di",
    "last_scan_utc",
    "gate_adx",
    "gate_conf",
    "gate_di",
]


def _path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(_REPO, p)


def parse_ts(s: str) -> Optional[dt.datetime]:
    if not s:
        return None
    s = str(s).replace("Z", "")
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def di_abs(r: dict) -> float:
    if r.get("di_abs") is not None:
        try:
            return float(r["di_abs"])
        except (TypeError, ValueError):
            pass
    try:
        return abs(float(r.get("plus_di") or 0) - float(r.get("minus_di") or 0))
    except (TypeError, ValueError):
        return 0.0


def bar_key(r: dict) -> str:
    bar = r.get("closed_1h_bar")
    if bar:
        return str(bar)
    ts = str(r.get("timestamp") or "")
    # e.g. 2026-09-10T07:16:46... -> 2026-09-10T07:00:00
    if len(ts) >= 13:
        return ts[:13] + ":00:00"
    return ts or "?"


def day_key(r: dict, bar: str) -> Optional[str]:
    """UTC calendar date for aggregation."""
    if bar and len(bar) >= 10 and bar[4] == "-" and bar[7] == "-":
        return bar[:10]
    ts = parse_ts(r.get("timestamp", ""))
    if ts is None:
        return None
    return ts.strftime("%Y-%m-%d")


def is_directional(r: dict) -> bool:
    pred = r.get("pred")
    if pred in (0, 2):
        return True
    name = (r.get("class_name") or "").strip()
    return name in ("Up", "Down", "SELL", "BUY")


def load_journal(path: str) -> List[dict]:
    rows: List[dict] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def first_fail_reason(
    adx: float, conf: float, di: float, adx_th: float, conf_th: float, di_th: float
) -> str:
    """Ordered first-fail matching paper_trader gate_stats."""
    if adx < adx_th:
        return "fail_adx"
    if conf < conf_th:
        return "fail_conf"
    if di < di_th:
        return "fail_di"
    return "PASS"


def aggregate_daily(
    rows: Iterable[dict],
    adx_th: float,
    conf_th: float,
    di_th: float,
    symbols: Optional[List[str]],
) -> Dict[str, dict]:
    """
    Return {date: stats_dict} using uniq (symbol, closed_1h_bar).
    Keep first occurrence per key (same as evaluate_signal_journal).
    """
    seen: set = set()
    # per-day accumulators
    days: Dict[str, dict] = {}

    def _day(d: str) -> dict:
        if d not in days:
            days[d] = {
                "date": d,
                "scan_total": 0,
                "no_dir": 0,
                "dir_total": 0,
                "PASS": 0,
                "fail_adx": 0,
                "fail_conf": 0,
                "fail_di": 0,
                "dir_rejected": 0,
                "near_max_adx": 0.0,
                "near_max_conf": 0.0,
                "near_max_di": 0.0,
                "last_scan_utc": "",
                "gate_adx": adx_th,
                "gate_conf": conf_th,
                "gate_di": di_th,
            }
        return days[d]

    for r in rows:
        sym = r.get("symbol")
        if symbols and sym not in symbols:
            continue
        bar = bar_key(r)
        key = (sym, bar)
        if key in seen:
            continue
        seen.add(key)

        d = day_key(r, bar)
        if not d:
            continue
        st = _day(d)
        st["scan_total"] += 1

        ts = parse_ts(r.get("timestamp", ""))
        if ts is not None:
            iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            if iso > st["last_scan_utc"]:
                st["last_scan_utc"] = iso

        try:
            adx = float(r.get("adx") or 0)
            conf = float(r.get("confidence") or 0)
        except (TypeError, ValueError):
            adx, conf = 0.0, 0.0
        di = di_abs(r)

        if adx > st["near_max_adx"]:
            st["near_max_adx"] = adx
        if conf > st["near_max_conf"]:
            st["near_max_conf"] = conf
        if di > st["near_max_di"]:
            st["near_max_di"] = di

        if not is_directional(r):
            st["no_dir"] += 1
            continue

        st["dir_total"] += 1
        reason = first_fail_reason(adx, conf, di, adx_th, conf_th, di_th)
        st[reason] += 1
        if reason != "PASS":
            st["dir_rejected"] += 1

    return days


def write_csv(path: str, days: Dict[str, dict]) -> int:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = [days[d] for d in sorted(days.keys())]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for st in rows:
            out = {
                "date": st["date"],
                "scan_total": int(st["scan_total"]),
                "no_dir": int(st["no_dir"]),
                "dir_total": int(st["dir_total"]),
                "PASS": int(st["PASS"]),
                "fail_adx": int(st["fail_adx"]),
                "fail_conf": int(st["fail_conf"]),
                "fail_di": int(st["fail_di"]),
                "dir_rejected": int(st["dir_rejected"]),
                "near_max_adx": f"{st['near_max_adx']:.4f}",
                "near_max_conf": f"{st['near_max_conf']:.4f}",
                "near_max_di": f"{st['near_max_di']:.4f}",
                "last_scan_utc": st["last_scan_utc"],
                "gate_adx": st["gate_adx"],
                "gate_conf": st["gate_conf"],
                "gate_di": st["gate_di"],
            }
            w.writerow(out)
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Export daily gate-reject CSV from signal journal")
    ap.add_argument(
        "--journal",
        default=SIGNAL_JOURNAL_FILE,
        help="path to signal_journal.jsonl (default from config)",
    )
    ap.add_argument(
        "--out",
        default="reports/gate_rejects_daily.csv",
        help="output CSV path (default reports/gate_rejects_daily.csv)",
    )
    args = ap.parse_args()

    journal_path = _path(args.journal)
    out_path = _path(args.out)
    adx_th = float(ADX_STRONG_THRESHOLD)
    conf_th = float(CONFIDENCE_THRESHOLD)
    di_th = float(MIN_DI_DIFF)
    symbols = list(TRADING_SYMBOLS) if TRADING_SYMBOLS else None

    rows = load_journal(journal_path)
    days = aggregate_daily(rows, adx_th, conf_th, di_th, symbols)
    n = write_csv(out_path, days)

    print(f"Journal: {journal_path} ({len(rows)} lines)")
    print(
        f"Gates (live, read-only): ADX>={adx_th:g} conf>={conf_th:g} |DI|>={di_th:g} "
        f"whitelist={symbols or 'ALL'}"
    )
    print(f"Wrote {out_path} ({n} day rows)")
    if days:
        keys = sorted(days.keys())
        print(f"Date range: {keys[0]} .. {keys[-1]}")
        for d in keys[-3:]:
            st = days[d]
            print(
                f"  {d}: scan={st['scan_total']} no_dir={st['no_dir']} "
                f"dir={st['dir_total']} PASS={st['PASS']} "
                f"fail_adx={st['fail_adx']} fail_conf={st['fail_conf']} "
                f"fail_di={st['fail_di']} dir_rej={st['dir_rejected']} "
                f"near_max_adx={st['near_max_adx']:.2f}"
            )
    else:
        print("No daily rows (empty journal or all filtered).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
