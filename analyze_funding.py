import ccxt
import pandas as pd
from datetime import datetime, timedelta

def analyze_funding():
    exchange = ccxt.binance()
    print("Fetching market data from Binance...")
    markets = exchange.load_markets()
    
    # Filter for USDT Perpetual futures
    symbols = [s for s in markets if markets[s]['linear'] and markets[s]['type'] == 'swap' and s.endswith('/USDT:USDT')]
    
    results = []
    print(f"Analyzing {len(symbols)} perpetual markets...")
    
    # We'll sample the top 20 by volume to ensure liquidity
    # For speed in this demo, we'll pick a few well-known high-yielders + majors
    targets = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'PEPE/USDT:USDT', 'DOGE/USDT:USDT']
    
    for symbol in targets:
        try:
            # Fetch current funding rate
            funding = exchange.fetch_funding_rate(symbol)
            rate = funding['fundingRate']
            
            # Estimate APR (3 payments per day * 365 days)
            apr = rate * 3 * 365 * 100
            
            # Fetch historical funding (last 30 intervals approx)
            # Note: Binance fetchFundingRateHistory is limited, but we'll try
            history = exchange.fetch_funding_rate_history(symbol, limit=30)
            avg_rate = sum([h['fundingRate'] for h in history]) / len(history)
            avg_apr = avg_rate * 3 * 365 * 100
            
            results.append({
                'Symbol': symbol.split(':')[0],
                'Current Rate': f"{rate*100:.4f}%",
                'Current APR': f"{apr:.2f}%",
                '30-Interval Avg APR': f"{avg_apr:.2f}%"
            })
        except Exception as e:
            continue
            
    df = pd.DataFrame(results)
    print("\n--- Funding Rate Arbitrage Opportunity Scan ---")
    print(df.to_string(index=False))
    print("\n*Note: Positive APR means Longs pay Shorts (You earn money by Shorting).")

if __name__ == "__main__":
    analyze_funding()
