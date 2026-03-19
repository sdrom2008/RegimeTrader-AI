"""批量下载多个币种的6年1小时数据"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_6y_data import fetch_historical_data

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

for symbol in symbols:
    try:
        filename = f"data/{symbol.replace('/','_')}_1h_6y.csv"
        print(f"\n=== Fetching {symbol} -> {filename} ===")
        fetch_historical_data(symbol=symbol, save_to=filename)
    except Exception as e:
        print(f"[!] {symbol} failed: {e}")
print("\n[+] All done!")
