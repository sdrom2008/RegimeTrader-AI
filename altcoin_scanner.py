import ccxt
import pandas as pd
import numpy as np
import datetime
import time

from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer

def fetch_top_symbols(exchange, limit=30):
    print("Fetching market tickers to find top volume symbols...")
    tickers = exchange.fetch_tickers()
    
    usdt_pairs = []
    for symbol, ticker in tickers.items():
        # Focus on USDT spot pairs, exclude leveraged tokens (UP/DOWN) and stablecoin pairs
        if symbol.endswith('/USDT') and ':' not in symbol and not any(x in symbol for x in ['UP/USDT', 'DOWN/USDT', 'USDC/USDT', 'TUSD/USDT', 'FDUSD/USDT']):
            if ticker['quoteVolume'] is not None:
                usdt_pairs.append({
                    'symbol': symbol,
                    'volume': ticker['quoteVolume']
                })
                
    # Sort by volume descending
    usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
    top_symbols = [pair['symbol'] for pair in usdt_pairs[:limit]]
    
    print(f"Top {limit} symbols by 24h volume selected.")
    return top_symbols

def scan_market():
    print(f"\n{'='*60}")
    print(f"🚀 REGIME TRADER AI - MULTI-COIN SCANNER")
    print(f"⏰ Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")

    exchange = ccxt.binance({'enableRateLimit': True})
    top_symbols = fetch_top_symbols(exchange, limit=40) # Scan top 40
    
    analyzer = MarketStateAnalyzer()
    
    buy_signals = []
    sell_signals = []
    
    print(f"\nScanning {len(top_symbols)} symbols on the Daily (1d) timeframe...\n")
    
    for symbol in top_symbols:
        try:
            # Fetch 250 days of data to ensure 200 EMA is accurate
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if len(df) < 200:
                continue # Not enough data for 200 EMA
                
            # Calculate custom indicators needed for our filters
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            
            # Run core regime analysis
            market_state, conf = analyzer.analyze(df)
            if market_state == "Insufficient Data":
                continue
                
            latest_row = df.iloc[-1]
            close_price = latest_row['Close']
            ema_200 = latest_row['EMA_200']
            rsi = latest_row['RSI']
            vol = latest_row['Volume']
            vol_sma = latest_row['Volume_SMA']
            
            # --- APPLY OUR STRICT FILTERS ---
            is_above_200ema = close_price > ema_200
            has_volume_support = vol > (vol_sma * 0.8)
            is_overbought = rsi > 85
            is_oversold = rsi < 30
            
            signal = "HOLD"
            reason = ""
            
            if market_state in ["Uptrend", "Volatile Uptrend"] and conf > 0.7:
                if not is_above_200ema:
                    pass # Filtered: Macro Downtrend
                elif not has_volume_support:
                    pass # Filtered: No volume
                elif is_overbought:
                    pass # Filtered: Overbought
                else:
                    signal = "BUY"
                    reason = f"Trend Breakout (Conf: {conf:.2f}, RSI: {rsi:.1f})"
                    buy_signals.append((symbol, close_price, reason))
                    
            elif market_state in ["Downtrend", "Volatile Downtrend"] and conf > 0.7:
                if is_above_200ema:
                    pass # Filtered: Macro Uptrend
                elif is_oversold:
                    pass # Filtered: Oversold
                else:
                    signal = "SELL"
                    reason = f"Bear Trend Breakout (Conf: {conf:.2f}, RSI: {rsi:.1f})"
                    sell_signals.append((symbol, close_price, reason))
                    
            # Print a subtle progress indicator
            time.sleep(0.1) # Respect rate limits
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            
    # --- REPORT RESULTS ---
    print(f"\n{'='*60}")
    print(f"🎯 SCAN COMPLETE. FOUND {len(buy_signals) + len(sell_signals)} ACTIONABLE SIGNALS.")
    print(f"{'='*60}\n")
    
    if buy_signals:
        print("🟢 LONG / BUY OPPORTUNITIES (Uptrend + Vol + >EMA200):")
        for sym, price, rsn in buy_signals:
            print(f"   [BUY] {sym:<10} | Price: ${price:<10.4f} | {rsn}")
    else:
        print("🟢 No high-quality BUY signals found today.")
        
    print("")
    
    if sell_signals:
        print("🔴 SHORT / SELL OPPORTUNITIES (Downtrend + <EMA200):")
        for sym, price, rsn in sell_signals:
            print(f"   [SELL] {sym:<10} | Price: ${price:<10.4f} | {rsn}")
    else:
        print("🔴 No high-quality SELL signals found today.")
        
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    scan_market()
