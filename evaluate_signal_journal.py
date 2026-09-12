#!/usr/bin/env python3
"""
Evaluate signal_journal.jsonl accuracy.

For each actionable signal (proposed_signal in BUY/SELL, gates_passed)
with age >= LOOK_FORWARD_CANDLES hours, compare close at signal time vs
forward close (~24h later on 1h bars).

  BUY  hit if close_fwd > close
  SELL hit if close_fwd < close

Uses stored close from journal + live OHLCV via data-api (same as paper_trader).
Writes reports/signal_accuracy_latest.md and prints hit rate by direction.
"""

from __future__ import annotations

import json
import os
import sys
import datetime
from collections import defaultdict

import ccxt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    LOOK_FORWARD_CANDLES,
    SIGNAL_JOURNAL_FILE,
    CONFIDENCE_THRESHOLD,
    ADX_STRONG_THRESHOLD,
)

_REPO = os.path.dirname(os.path.abspath(__file__))


def _path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(_REPO, p)


def make_exchange():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'fetchMarkets': ['spot'],
            'fetchCurrencies': False,
        },
    })
    _pub = 'https://data-api.binance.vision'
    exchange.urls['api']['public'] = f'{_pub}/api/v3'
    exchange.urls['api']['private'] = f'{_pub}/api/v3'
    exchange.urls['api']['v1'] = f'{_pub}/api/v1'
    return exchange


def parse_ts(s: str) -> datetime.datetime:
    s = str(s).replace('Z', '')
    return datetime.datetime.fromisoformat(s)


def load_journal(path: str) -> list:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def fetch_forward_close(exchange, symbol: str, signal_ts: datetime.datetime, hours: int):
    """Fetch 1h OHLCV and return close ~hours after signal_ts (same timeframe proxy)."""
    # Need enough bars: from signal to now; also look back a bit for indexing
    since_ms = int((signal_ts - datetime.timedelta(hours=2)).timestamp() * 1000)
    limit = max(hours + 10, 50)
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', since=since_ms, limit=limit)
    if not ohlcv:
        return None, None
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    target = signal_ts + datetime.timedelta(hours=hours)
    # Pick bar at or just after target
    fwd = df[df['timestamp'] >= target]
    if fwd.empty:
        # Not enough history yet
        return None, None
    row = fwd.iloc[0]
    return float(row['Close']), row['timestamp'].to_pydatetime()


def main():
    journal_path = _path(SIGNAL_JOURNAL_FILE)
    rows = load_journal(journal_path)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    horizon = int(LOOK_FORWARD_CANDLES)

    actionable_raw = [
        r for r in rows
        if r.get('gates_passed') and r.get('proposed_signal') in ('BUY', 'SELL')
    ]
    # 5min scan duplicates the same closed 1h bar — keep first per (symbol, bar)
    seen = set()
    actionable = []
    for r in actionable_raw:
        bar = r.get('closed_1h_bar') or (str(r.get('timestamp', ''))[:13] + ':00')
        key = (r.get('symbol'), bar, r.get('proposed_signal'))
        if key in seen:
            continue
        seen.add(key)
        actionable.append(r)

    print(f"Journal: {journal_path}")
    print(
        f"Total lines: {len(rows)} | Actionable raw: {len(actionable_raw)} | "
        f"deduped: {len(actionable)}"
    )
    print(f"Horizon: {horizon}h | Conf>={CONFIDENCE_THRESHOLD} ADX>={ADX_STRONG_THRESHOLD}")

    exchange = make_exchange()
    results = []
    pending = 0
    by_dir = defaultdict(lambda: {'n': 0, 'hits': 0})

    for r in actionable:
        try:
            ts = parse_ts(r['timestamp'])
        except Exception:
            continue
        age_h = (now - ts).total_seconds() / 3600.0
        if age_h < horizon:
            pending += 1
            continue

        symbol = r['symbol']
        direction = r['proposed_signal']
        close0 = float(r['close'])
        close_fwd, fwd_ts = fetch_forward_close(exchange, symbol, ts, horizon)
        if close_fwd is None:
            pending += 1
            continue

        if direction == 'BUY':
            hit = close_fwd > close0
        else:
            hit = close_fwd < close0

        ret = (close_fwd - close0) / close0 if close0 else 0.0
        rec = {
            'timestamp': r['timestamp'],
            'symbol': symbol,
            'direction': direction,
            'pred': r.get('pred'),
            'confidence': r.get('confidence'),
            'adx': r.get('adx'),
            'close': close0,
            'close_fwd': close_fwd,
            'fwd_ts': fwd_ts.isoformat() + 'Z' if fwd_ts else None,
            'return_pct': ret * 100.0,
            'hit': hit,
        }
        results.append(rec)
        by_dir[direction]['n'] += 1
        if hit:
            by_dir[direction]['hits'] += 1

        print(
            f"{'HIT' if hit else 'MISS'} {direction:4} {symbol:10} "
            f"close={close0:.4f} fwd={close_fwd:.4f} ret={ret*100:+.2f}% "
            f"conf={float(r.get('confidence') or 0):.3f}"
        )

    total_n = sum(v['n'] for v in by_dir.values())
    total_hits = sum(v['hits'] for v in by_dir.values())
    overall = (total_hits / total_n * 100.0) if total_n else 0.0

    print("\n=== Hit rate by direction ===")
    lines = []
    for d in ('BUY', 'SELL'):
        n = by_dir[d]['n']
        h = by_dir[d]['hits']
        rate = (h / n * 100.0) if n else 0.0
        print(f"  {d}: {h}/{n} = {rate:.1f}%")
        lines.append(f"| {d} | {h} | {n} | {rate:.1f}% |")

    print(f"  ALL: {total_hits}/{total_n} = {overall:.1f}%")
    print(f"Pending (age < {horizon}h or no fwd bar): {pending}")

    # Markdown report
    os.makedirs(os.path.join(_REPO, 'reports'), exist_ok=True)
    out_md = os.path.join(_REPO, 'reports', 'signal_accuracy_latest.md')
    generated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    md = []
    md.append('# Signal accuracy (observe journal)')
    md.append('')
    md.append(f'- Generated: `{generated}` (local)')
    md.append(f'- Journal: `{SIGNAL_JOURNAL_FILE}`')
    md.append(f'- Horizon: `{horizon}` × 1h bars')
    md.append(f'- Gates: ADX>={ADX_STRONG_THRESHOLD}, conf>={CONFIDENCE_THRESHOLD}, DI agrees')
    md.append(f'- Rule: BUY hit if close_fwd>close; SELL hit if close_fwd<close')
    md.append('')
    md.append('## Hit rate by direction')
    md.append('')
    md.append('| Direction | Hits | N | Hit rate |')
    md.append('|---|---:|---:|---:|')
    md.extend(lines)
    md.append(f'| **ALL** | {total_hits} | {total_n} | **{overall:.1f}%** |')
    md.append('')
    md.append(f'- Pending (too young / missing fwd): {pending}')
    md.append(f'- Actionable journal rows (deduped): {len(actionable)}')
    md.append(f'- Actionable raw (pre-dedupe): {len(actionable_raw)}')
    md.append(f'- Total journal rows: {len(rows)}')
    md.append('')
    if results:
        md.append('## Evaluated signals')
        md.append('')
        md.append('| Time (UTC) | Symbol | Dir | Close | Fwd | Ret% | Hit | Conf |')
        md.append('|---|---|---|---:|---:|---:|:---:|---:|')
        for rec in results[-50:]:  # last 50
            md.append(
                f"| {rec['timestamp'][:19]} | {rec['symbol']} | {rec['direction']} | "
                f"{rec['close']:.4f} | {rec['close_fwd']:.4f} | {rec['return_pct']:+.2f} | "
                f"{'Y' if rec['hit'] else 'N'} | {float(rec.get('confidence') or 0):.3f} |"
            )
        md.append('')
    else:
        md.append('_No matured actionable signals yet. Re-run after ≥24h of observe logging._')
        md.append('')

    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print(f"\nWrote {out_md}")


if __name__ == '__main__':
    main()
