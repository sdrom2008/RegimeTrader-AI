import ccxt
import pandas as pd
import numpy as np

def market_report():
    exchange = ccxt.binance()
    symbols = ['BTC/USDT', 'XRP/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'LINK/USDT']
    
    # Fetch current prices
    tickers = exchange.fetch_tickers(symbols)
    prices = {s: tickers[s]['last'] for s in symbols}
    
    report_data = []
    
    print(f"Market Snapshot - {pd.Timestamp.now()}")
    print("-" * 40)
    
    for symbol in symbols[1:]: # Skip BTC
        # Fetch 24h history (24 points of 1h)
        ohlcv_btc = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=24)
        ohlcv_alt = exchange.fetch_ohlcv(symbol, '1h', limit=24)
        
        btc_c = np.array([o[4] for o in ohlcv_btc])
        alt_c = np.array([o[4] for o in ohlcv_alt])
        
        ratios = btc_c / alt_c
        curr_ratio = prices['BTC/USDT'] / prices[symbol]
        
        mean_ratio = ratios.mean()
        std_ratio = ratios.std()
        zscore = (curr_ratio - mean_ratio) / std_ratio
        
        report_data.append({
            'Pair': f"BTC-{symbol.split('/')[0]}",
            'Ratio': curr_ratio,
            'Z-Score': zscore,
            'Status': "Overvalued" if zscore > 1.5 else "Undervalued" if zscore < -1.5 else "Neutral"
        })

    df = pd.DataFrame(report_data)
    print(f"BTC Current: ${prices['BTC/USDT']:,.2f}")
    print("\n--- Golden Pair Ratio Analysis ---")
    print(df.to_string(index=False, formatters={
        'Ratio': '{:,.2f}'.format,
        'Z-Score': '{:,.2f}'.format
    }))
    print("\n* Z-Score > 2.0: BTC is relative Strong (Sell BTC/Buy Alt)")
    print("* Z-Score < -2.0: BTC is relative Weak (Buy BTC/Sell Alt)")

if __name__ == "__main__":
    market_report()
