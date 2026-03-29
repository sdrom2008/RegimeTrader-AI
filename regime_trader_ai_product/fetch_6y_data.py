"""
下载 BTC/USDT 6年1小时K线数据并生成特征
使用 ccxt 从 Binance 获取
"""

import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta

def fetch_historical_data(symbol='BTC/USDT', years=6, save_to=None):
    exchange = ccxt.binance({'enableRateLimit': True})

    if save_to is None:
        safe_symbol = symbol.replace('/','_')
        save_to = f'data/{safe_symbol}_1h_6y.csv'

    # 计算时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(days=years*365)
    since = int(start_time.timestamp() * 1000)
    limit = 1000  # 每次请求最大数量

    print(f"[*] Fetching {symbol} 1h data from {start_time.date()} to {end_time.date()}")

    all_ohlcv = []
    while since < end_time.timestamp() * 1000:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', since=since, limit=limit)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1  # 下一小时的开始时间
            print(f"  Fetched {len(all_ohlcv)} rows so far...")
            time.sleep(0.5)  # API限流
        except Exception as e:
            print(f"[!] Error fetching data: {e}")
            time.sleep(5)

    # 转为DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # 去重
    df = df[~df.index.duplicated(keep='first')]

    # 保存
    df.to_csv(save_to)
    print(f"[+] Saved {len(df)} rows to {save_to}")

    return df

if __name__ == '__main__':
    fetch_historical_data()
