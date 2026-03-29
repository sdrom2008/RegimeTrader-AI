import ccxt
import pandas as pd
import time
import os

def fetch_historical_data(symbol='BTC/USDT', timeframe='1h', years=2):
    """
    Fetches historical OHLCV data from Binance.
    """
    print(f"[*] Fetching historical data for {symbol} on {timeframe} timeframe...")
    
    # Initialize exchange
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Calculate required limit and since timestamp
    limit = 24 * 365 * years  # Approx number of candles
    since = exchange.parse8601(f'{pd.Timestamp.now().year - years}-01-01T00:00:00Z')
    
    # Create data directory
    if not os.path.exists('data'):
        os.makedirs('data')
        
    filename = f"data/{symbol.replace('/', '_')}_{timeframe}_{years}y.csv"
    
    try:
        # Fetch data
        all_ohlcv = []
        while since < exchange.milliseconds():
            print(f"[*] Fetching chunk starting from {exchange.iso8601(since)}...")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            since = ohlcv[-1][0] + exchange.parse_timeframe(timeframe) * 1000
            all_ohlcv.extend(ohlcv)
            time.sleep(exchange.rateLimit / 1000) # Respect rate limits

        print(f"[*] Fetched a total of {len(all_ohlcv)} candles.")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Save to CSV
        df.to_csv(filename)
        print(f"[+] Successfully saved data to {filename}")
        return filename
        
    except Exception as e:
        print(f"[!] An error occurred: {e}")
        return None

if __name__ == '__main__':
    fetch_historical_data()
