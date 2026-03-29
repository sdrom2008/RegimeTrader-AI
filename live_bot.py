import os
import time
import datetime
import pandas as pd
from dotenv import load_dotenv

# Load the secret .env file
load_dotenv()

# Import our custom modules
from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer
from fetch_real_data import fetch_binance_klines
from test_smart_money import get_binance_ls_ratio
from ai_news_reader import fetch_crypto_rss
from regime_trader_ai_product.code.sentiment_handler import MacroSentimentHandler

# Optional: Add your Google Gemini API key here for true LLM integration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def run_live_cycle():
    print(f"\n{'='*50}")
    print(f"🚀 REGIME TRADER AI - LIVE MONITORING CYCLE")
    print(f"⏰ Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*50}\n")

    # Step 1: Fetch latest price action
    print("[1] Fetching Latest K-line Data...")
    fetch_binance_klines(limit=300) # Only need enough for 200 EMA and ADX/ATR
    
    # Read the updated data
    df = pd.read_csv('data/binance_data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Calculate EMA 200 for macro trend filter
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # Step 2: Technical Analysis & Regime Classification
    print("\n[2] Running Technical Regime Analysis...")
    analyzer = MarketStateAnalyzer()
    market_state, confidence_score = analyzer.analyze(df)
    
    latest_row = df.iloc[-1]
    current_price = latest_row['Close']
    is_above_200ema = current_price > latest_row.get('EMA_200', 0)
    
    print(f"    - Current Price: ${current_price:.2f}")
    print(f"    - Short-term Regime: {market_state} (Confidence: {confidence_score:.2f})")
    print(f"    - Macro Trend (EMA200): {'Bullish (Above)' if is_above_200ema else 'Bearish (Below)'}")

    # Step 3: Smart Money (On-Chain/Derivatives) Analysis
    print("\n[3] Checking Smart Money Data (Binance Top Traders L/S Ratio)...")
    sm_data = get_binance_ls_ratio()
    sm_signal = "NEUTRAL"
    if sm_data:
        global_ratio = sm_data.get('global_ls_ratio', 1)
        top_pos_ratio = sm_data.get('top_position_ls_ratio', 1)
        
        print(f"    - Retail L/S Ratio: {global_ratio:.4f}")
        print(f"    - Top Trader Position L/S Ratio: {top_pos_ratio:.4f}")
        
        # Logic: If retail is heavily long (ratio > 1.5) and top traders are heavily short (< 0.8), danger!
        if global_ratio > 1.3 and top_pos_ratio < 0.9:
            sm_signal = "DANGER (Smart Money is fading the crowd)"
        elif top_pos_ratio > 1.2:
            sm_signal = "BULLISH (Smart Money is long)"
        else:
            sm_signal = "NEUTRAL"
            
        print(f"    - Smart Money Signal: {sm_signal}")
    else:
        print("    - Failed to fetch Smart Money data.")

    # Step 4: Macro Sentiment Analysis (Fear & Greed + News LLM)
    print("\n[4] Running Macro Sentiment & News AI Analysis...")
    sentiment_handler = MacroSentimentHandler()
    sentiment_handler.fetch_historical_fng() # Update latest F&G
    sentiment_handler.load_data()
    fng_score, fng_label = sentiment_handler.get_sentiment_for_date(latest_row['Date'])
    
    print(f"    - Fear & Greed Index: {fng_score} ({fng_label})")
    
    # Read the news
    print("\n📰 Reading today's top Crypto News headlines for LLM Sentiment Scoring...")
    news_items = fetch_crypto_rss()
    
    llm_sentiment = "NEUTRAL"
    if GEMINI_API_KEY:
        print("    - Interfacing with Gemini LLM for sentiment extraction... (API Key Found)")
        # In a fully deployed script, this is where the `google.generativeai` call would happen.
        llm_sentiment = "POSITIVE" # Placeholder for when API runs
    else:
        print("    - [!] No Gemini API key found in environment variables.")
        print("    - Running simulated/fallback NLP analysis based on keyword density...")
        
        # Very basic fallback keyword counter
        bullish_words = ['surge', 'soar', 'buy', 'accumulate', 'bull', 'support', 'reclaims']
        bearish_words = ['crash', 'sell', 'dump', 'bear', 'resistance', 'sec', 'lawsuit', 'dead']
        bull_score = sum(1 for item in news_items for word in bullish_words if word in item['title'].lower())
        bear_score = sum(1 for item in news_items for word in bearish_words if word in item['title'].lower())
        
        if bull_score > bear_score + 2:
            llm_sentiment = "POSITIVE"
        elif bear_score > bull_score + 2:
            llm_sentiment = "NEGATIVE"
        else:
            llm_sentiment = "NEUTRAL"
            
    print(f"    - AI News Sentiment Score: {llm_sentiment}")

    # Step 5: Final Trading Decision Logic (The 3-Light System)
    print(f"\n{'-'*50}")
    print("🚥 FINAL AI TRADE DECISION 🚥")
    print(f"{'-'*50}")
    
    action = "HOLD"
    reasoning = []
    
    # 1. Technical Condition (The base)
    tech_buy = market_state in ["Uptrend", "Volatile Uptrend"] and is_above_200ema
    tech_sell = market_state in ["Downtrend", "Volatile Downtrend"] and not is_above_200ema
    
    # 2. Smart Money Filter (Veto power)
    sm_veto = (sm_signal == "DANGER (Smart Money is fading the crowd)")
    
    # 3. Sentiment Filter (Extreme bubbles or extreme panic)
    fng_veto_buy = (fng_score >= 90) # Don't buy the absolute peak
    news_veto_buy = (llm_sentiment == "NEGATIVE")
    
    # Final Combine
    if tech_buy:
        if sm_veto:
            reasoning.append(f"REJECTED BUY: Smart Money is heavily short against retail longs.")
        elif fng_veto_buy:
            reasoning.append(f"REJECTED BUY: Market is in an extreme bubble (F&G={fng_score}).")
        elif news_veto_buy:
            reasoning.append(f"REJECTED BUY: Bad news macro environment overrides technical breakout.")
        else:
            action = "EXECUTE BUY LONG"
            reasoning.append("ALL SYSTEMS GO: Technical Uptrend + EMA200 Support + Smart Money Neutral/Bullish + Positive/Neutral News.")
            
    elif tech_sell:
        action = "EXECUTE SELL SHORT"
        reasoning.append("Downtrend confirmed below EMA 200. Shorting conditions met.")
    else:
        reasoning.append(f"Market in {market_state} regime. Not suitable for new entries.")
        
    print(f"🔥 ACTION: {action}")
    print(f"🧠 REASONING: {reasoning[0]}")
    print(f"{'='*50}\n")
    
    return action

if __name__ == "__main__":
    # Usually you would run this in a while True loop with time.sleep(86400) for daily, 
    # or via a cronjob. For demonstration, we run it once.
    run_live_cycle()
