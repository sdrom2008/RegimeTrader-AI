"""Robust Binance public OHLCV fetch via data-api.binance.vision (geo-unrestricted).
Retries, resume/checkpoint, rate-limit sleep. Naming matches fetch_6y_data.py.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import ccxt
import pandas as pd

SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
TIMEFRAME = "1h"
YEARS = 6
LIMIT = 1000
MAX_RETRIES = 8
BASE_SLEEP = 0.2
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def make_exchange():
    ex = ccxt.binance({
        "enableRateLimit": True,
        "options": {"defaultType": "spot", "fetchMarkets": ["spot"]},
    })
    # api.binance.com returns 451 from restricted regions
    ex.urls["api"]["public"] = "https://data-api.binance.vision/api/v3"
    return ex


def out_path(symbol: str) -> str:
    return os.path.join(DATA_DIR, f"{symbol.replace('/', '_')}_{TIMEFRAME}_{YEARS}y.csv")


def load_existing(path: str):
    if not os.path.exists(path) or os.path.getsize(path) < 50:
        return None
    df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
    if df.empty:
        return None
    return df


def fetch_symbol(exchange, symbol: str) -> pd.DataFrame:
    path = out_path(symbol)
    now = datetime.now(timezone.utc)
    end_ms = int(now.timestamp() * 1000)
    start_ms = int((now - timedelta(days=YEARS * 365)).timestamp() * 1000)

    existing = load_existing(path)
    if existing is not None:
        last_ts = int(pd.Timestamp(existing.index.max()).timestamp() * 1000)
        since = last_ts + 1
        base_df = existing.copy()
        print(f"[*] {symbol}: resume from {existing.index.max()} ({len(existing)} rows)", flush=True)
    else:
        since = start_ms
        base_df = None
        print(f"[*] {symbol}: fresh fetch from {datetime.fromtimestamp(start_ms/1000, tz=timezone.utc).date()}", flush=True)

    if base_df is not None and since >= end_ms - 3600_000:
        print(f"[+] {symbol}: already up to date ({len(base_df)} rows)", flush=True)
        return base_df

    batch = []
    retries = 0
    while since < end_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=LIMIT)
            retries = 0
            if not ohlcv:
                break
            next_since = ohlcv[-1][0] + 1
            if next_since <= since:
                break
            batch.extend(ohlcv)
            since = next_since
            if len(batch) == LIMIT or len(batch) % 5000 < LIMIT:
                ts = datetime.fromtimestamp(ohlcv[-1][0] / 1000, tz=timezone.utc)
                print(f"  {symbol}: {len(batch)} new rows (thru {ts})", flush=True)
            if len(batch) >= 10000:
                chunk = pd.DataFrame(batch, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
                chunk["timestamp"] = pd.to_datetime(chunk["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
                chunk = chunk.set_index("timestamp")
                df = pd.concat([base_df, chunk]) if base_df is not None else chunk
                df = df[~df.index.duplicated(keep="last")].sort_index()
                df.to_csv(path)
                base_df = df
                batch = []
                print(f"  [checkpoint] {symbol}: saved {len(df)} rows -> {path}", flush=True)
            time.sleep(BASE_SLEEP)
        except (ccxt.RateLimitExceeded, ccxt.DDoSProtection) as e:
            wait = min(60, 2 ** retries)
            print(f"[!] {symbol} rate limit: {e}; sleep {wait}s", flush=True)
            time.sleep(wait)
            retries += 1
            if retries > MAX_RETRIES:
                raise
        except Exception as e:
            wait = min(60, 2 ** retries)
            print(f"[!] {symbol} error: {e}; sleep {wait}s (retry {retries+1}/{MAX_RETRIES})", flush=True)
            time.sleep(wait)
            retries += 1
            if retries > MAX_RETRIES:
                raise

    if batch:
        chunk = pd.DataFrame(batch, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
        chunk["timestamp"] = pd.to_datetime(chunk["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
        chunk = chunk.set_index("timestamp")
        df = pd.concat([base_df, chunk]) if base_df is not None else chunk
    elif base_df is not None:
        df = base_df
    else:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    df = df[~df.index.duplicated(keep="last")].sort_index()
    cutoff = pd.Timestamp((now - timedelta(days=YEARS * 365)).replace(tzinfo=None))
    df = df[df.index >= cutoff]
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(path)
    print(f"[+] {symbol}: saved {len(df)} rows [{df.index.min()} .. {df.index.max()}] -> {path}", flush=True)
    return df


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    exchange = make_exchange()
    exchange.load_markets()
    print(f"[*] markets loaded ({len(exchange.markets)}) via data-api.binance.vision", flush=True)
    for symbol in SYMBOLS:
        try:
            fetch_symbol(exchange, symbol)
        except Exception as e:
            print(f"[!!] {symbol} FAILED: {e}", flush=True)
    print("\n[+] All done!", flush=True)


if __name__ == "__main__":
    main()
