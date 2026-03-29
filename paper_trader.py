import os
import json
import time
import datetime
import pandas as pd
import ccxt
from dotenv import load_dotenv
import pickle

# Import our custom modules
from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer
from test_smart_money import get_binance_ls_ratio
from ai_news_reader import fetch_crypto_rss

# Try to import pandas_ta, if not present, guide user.
try:
    import pandas_ta as ta
except ImportError:
    print("[!] pandas_ta is not installed. In your venv, run: pip install pandas_ta")
    exit()

load_dotenv()

STATE_FILE = 'paper_trade_state.json'
LEVERAGE = 3.0
INITIAL_CAPITAL = 10000.0
RISK_PER_TRADE_PCT = 0.05 # 5% risk of total capital per trade

# --- FEATURE LIST (must match the training script) ---
# This list ensures that we always use the same features for prediction as for training.
MODEL_FEATURES = [
    'ADX_14', 'ADXR_14_2', 'DMP_14', 'DMN_14', 'BBL_20_2.0_2.0', 
    'BBM_20_2.0_2.0', 'BBU_20_2.0_2.0', 'BBB_20_2.0_2.0', 'BBP_20_2.0_2.0', 
    'ATRr_14', 'RSI_14', 'EMA_50', 'EMA_200', 'BB_WIDTH', 'RSI_STD_20', 
    'PRICE_EMA200_DIST'
]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'capital': INITIAL_CAPITAL, 'positions': {}, 'trade_history': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def calculate_features(df):
    """Calculates all necessary features for the AI model."""
    df.ta.adx(length=14, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df['BB_WIDTH'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0']
    df['RSI_STD_20'] = df['RSI_14'].rolling(window=20).std()
    df['PRICE_EMA200_DIST'] = (df['Close'] - df['EMA_200']) / df['EMA_200']
    df.dropna(inplace=True)
    return df

def run_paper_trader():
    print(f"\n{'='*60}")
    print(f"🚀 AI-POWERED REGIME TRADER - 3X LEVERAGE ENGINE")
    print(f"⏰ Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*60}\n")
    
    # --- Load AI Regime Model ---
    model_filename = 'regime_model.pkl'
    try:
        with open(model_filename, 'rb') as f:
            regime_model = pickle.load(f)
        print(f"✅ AI Regime Model '{model_filename}' loaded successfully.")
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: AI model '{model_filename}' not found. Cannot proceed.")
        return

    state = load_state()
    print(f"💰 Current Paper Capital: ${state['capital']:.2f} (Leverage: {LEVERAGE}x)")
    print(f"📦 Open Positions: {len(state['positions'])}")

    # [UNCHANGED] Macro Filters (News, Smart Money) ...
    sentiment_label, sentiment_score = get_llm_news_sentiment()
    sm_data = get_binance_ls_ratio()
    sm_signal = "NEUTRAL"
    if sm_data:
        global_ratio = sm_data.get('global_ls_ratio', 1)
        top_pos_ratio = sm_data.get('top_position_ls_ratio', 1)
        if global_ratio > 1.5 and top_pos_ratio < 0.8: sm_signal = "BEARISH"
        elif top_pos_ratio > 1.3: sm_signal = "BULLISH"
    global_long_veto = (sentiment_label == "NEGATIVE") or (sm_signal == "BEARISH")
    global_short_veto = (sentiment_label == "POSITIVE")

    # [UNCHANGED] Update existing positions ...
    exchange = ccxt.binance({'enableRateLimit': True})
    to_remove = []
    for symbol, pos in state['positions'].items():
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            if pos['type'] == 'BUY':
                if current_price > pos.get('highest_seen', pos['entry_price']):
                    pos['highest_seen'] = current_price
                    pos['sl'] = max(pos['sl'], pos['highest_seen'] - (pos['atr'] * 1.5))
                if current_price <= pos['sl']:
                    pnl = (pos['sl'] - pos['entry_price']) * pos['amount']
                    state['capital'] += (pos['margin'] + pnl)
                    print(f"    ❌ CLOSED {symbol} LONG at SL {pos['sl']:.4f} | PnL: ${pnl:.2f}")
                    to_remove.append(symbol)
            elif pos['type'] == 'SELL':
                if current_price < pos.get('lowest_seen', pos['entry_price']):
                    pos['lowest_seen'] = current_price
                    pos['sl'] = min(pos['sl'], pos['lowest_seen'] + (pos['atr'] * 1.5))
                if current_price >= pos['sl']:
                    pnl = (pos['entry_price'] - pos['sl']) * pos['amount']
                    state['capital'] += (pos['margin'] + pnl)
                    print(f"    ❌ CLOSED {symbol} SHORT at SL {pos['sl']:.4f} | PnL: ${pnl:.2f}")
                    to_remove.append(symbol)
        except Exception as e: print(f"    Error updating {symbol}: {e}")
    for sym in to_remove:
        if sym in state['positions']: del state['positions'][sym]

    # --- Scan for new opportunities using the AI Model ---
    print("\n[🧠] Scanning Market with AI Brain...")
    analyzer = MarketStateAnalyzer()
    tickers = exchange.fetch_tickers()
    usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
    usdt_pairs.sort(key=lambda s: tickers[s]['quoteVolume'] or 0, reverse=True)
    top_symbols = usdt_pairs[:40] # Scan more symbols as AI is the main filter

    for symbol in top_symbols:
        if symbol in state['positions']: continue
        time.sleep(0.1)
        try:
            # 1. Fetch data & calculate features
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            if len(df) < 200: continue
            df_features = calculate_features(df.copy())
            if df_features.empty: continue
            
            # 2. Get latest features and predict regime
            latest_features = df_features[MODEL_FEATURES].iloc[-1].values.reshape(1, -1)
            regime_pred = regime_model.predict(latest_features)[0]

            # 3. AI-driven decision
            if regime_pred == 0: # AI predicts RANGE
                print(f"    - {symbol}: AI predicts RANGE. Skipping.")
                continue
            
            # AI predicts TREND, so proceed with trend-following logic
            print(f"    - {symbol}: AI predicts TREND! Evaluating entry...")
            market_state, conf = analyzer.analyze(df)
            latest = df.iloc[-1]
            price = latest['Close']
            atr = df_features.iloc[-1]['ATRr_14']
            
            # LONG ENTRY (only if AI said TREND)
            if market_state in ["Uptrend", "Volatile Uptrend"] and conf > 0.7:
                if global_long_veto:
                    print(f"        🛡️ BUY signal blocked by Global Macro Veto.")
                    continue
                # Position Sizing & Execution
                sl_dist = atr * 1.5
                risk_amount = state['capital'] * RISK_PER_TRADE_PCT
                notional_size = (risk_amount / sl_dist) * price
                margin_required = notional_size / LEVERAGE
                if (state['capital'] - sum(p['margin'] for p in state['positions'].values())) > margin_required:
                    # ... (Execute Buy)
                    print(f"        🎯 EXECUTED PAPER BUY: {symbol} @ ${price:.4f}")

            # SHORT ENTRY (only if AI said TREND)
            elif market_state in ["Downtrend", "Volatile Downtrend"] and conf > 0.7:
                if global_short_veto:
                    print(f"        🛡️ SELL signal blocked by Global Macro Veto.")
                    continue
                # Position Sizing & Execution
                sl_dist = atr * 1.5
                risk_amount = state['capital'] * RISK_PER_TRADE_PCT
                notional_size = (risk_amount / sl_dist) * price
                margin_required = notional_size / LEVERAGE
                if (state['capital'] - sum(p['margin'] for p in state['positions'].values())) > margin_required:
                    # ... (Execute Sell)
                    print(f"        🎯 EXECUTED PAPER SELL: {symbol} @ ${price:.4f}")

        except Exception as e: pass

    save_state(state)
    print(f"\n--- 📊 FINAL REPORT ---")
    # ... (Final report logic is unchanged)

if __name__ == "__main__":
    run_paper_trader()
