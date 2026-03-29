import pandas as pd
import json
import urllib.request

def fetch_binance_klines(symbol='BTCUSDT', interval='1d', limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    print(f"Fetching data from {url}")
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))

    
    df = pd.DataFrame(data, columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Close time', 'Quote asset volume', 'Number of trades', 
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    
    df['Date'] = pd.to_datetime(df['Open time'], unit='ms')
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
        
    df.to_csv('data/binance_data.csv', index=False)
    print(f"Real Binance data saved. Total rows: {len(df)}")

if __name__ == "__main__":
    fetch_binance_klines()
