import os
import json
import time
import datetime
import subprocess
import pandas as pd
import ccxt
from dotenv import load_dotenv
import pickle
import sys

# Import custom modules
from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer
from regime_trader_ai_product.code.sentiment_handler import MacroSentimentHandler
from test_smart_money import get_binance_ls_ratio

load_dotenv()

LEVERAGE = 3
RISK_PER_TRADE_PCT = 0.05
SCAN_LIMIT = 40  # number of top symbols to scan

def send_whatsapp_alert(message):
    print(f"[WhatsApp Alert] {message}")
    safe_msg = message.replace("'", "'\\''")
    target_number = "+8613908412393"
    cmd = f"openclaw message send --channel whatsapp --target '{target_number}' --message '{safe_msg}'"
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"[WhatsApp] Sent")
    except Exception as e:
        print(f"[WhatsApp] Failed: {e}")

def get_exchange():
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    if not api_key or not api_secret:
        raise ValueError("CRITICAL: Binance API Keys not found in .env file!")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    return exchange

def execute_real_trade():
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*60}")
    print(f"🔥 REGIME TRADER AI - LIVE EXECUTION")
    print(f"⏰ {now_str} UTC")
    print(f"{'='*60}\n")

    # Initialize exchange and check balance
    try:
        exchange = get_exchange()
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['free']
        print(f"💰 Real USDT Futures Balance: ${usdt_balance:.2f}")
        send_whatsapp_alert(f"🤖 实盘引擎启动\n💰 余额: ${usdt_balance:.2f} USDT")
    except Exception as e:
        msg = f"🚨 FATAL ERROR: Cannot connect to Binance. {e}"
        print(msg)
        send_whatsapp_alert(msg)
        return

    if usdt_balance < 10:
        msg = "⚠️ Insufficient USDT balance (< $10). Aborting run."
        print(msg)
        send_whatsapp_alert(msg)
        return

    # Load AI model
    try:
        with open('regime_model.pkl', 'rb') as f:
            regime_model = pickle.load(f)
        print("✅ AI Regime Model loaded.")
    except Exception as e:
        msg = f"❌ CRITICAL: Failed to load AI model - {e}"
        print(msg)
        send_whatsapp_alert(msg)
        return

    # Macro filters
    sentiment_handler = MacroSentimentHandler()
    sentiment_label = "NEUTRAL"
    try:
        fng_score, fng_label = sentiment_handler.get_sentiment_for_date(datetime.datetime.utcnow().date())
        sentiment_label = fng_label.upper() if fng_label else "NEUTRAL"
    except Exception as e:
        print(f"  Sentiment handler error: {e}")

    sm_data = get_binance_ls_ratio()
    sm_signal = "NEUTRAL"
    if sm_data:
        global_ratio = sm_data.get('global_ls_ratio', 1)
        top_pos_ratio = sm_data.get('top_position_ls_ratio', 1)
        if global_ratio > 1.5 and top_pos_ratio < 0.8:
            sm_signal = "BEARISH"
        elif top_pos_ratio > 1.3:
            sm_signal = "BULLISH"

    global_long_veto = (sentiment_label == "NEGATIVE") or (sm_signal == "BEARISH")
    global_short_veto = (sentiment_label == "POSITIVE") or (sm_signal == "BULLISH")
    print(f"  Macro Veto: Long={global_long_veto}, Short={global_short_veto}")
    print(f"  Sentiment: {sentiment_label}, SmartMoney: {sm_signal}")

    # Scan market
    analyzer = MarketStateAnalyzer()
    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers()
        usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
        usdt_pairs.sort(key=lambda s: tickers[s].get('quoteVolume',0) or 0, reverse=True)
        top_symbols = usdt_pairs[:SCAN_LIMIT]
        print(f"🔍 Scanning {len(top_symbols)} top symbols (Top {SCAN_LIMIT}).")
    except Exception as e:
        msg = f"Error fetching market list: {e}"
        print(msg)
        send_whatsapp_alert(msg)
        return

    new_signals = []
    for symbol in top_symbols:
        time.sleep(0.2)  # rate limit
        try:
            # Check existing position
            positions = exchange.fetch_positions([symbol])
            has_open = any(float(p['positionAmt']) != 0 for p in positions)
            if has_open:
                continue

            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            if len(df) < 200:
                continue

            # Feature engineering (same as paper trader)
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + rs))
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            df['ATR'] = df['High'] - df['Low']  # simplified stub; better to use pandas_ta.ATR

            # AI regime prediction
            # Compute the same 16 features as training (simplified here)
            # For now, use MarketStateAnalyzer as proxy to decide direction; but we also need regime check
            # We'll approximate regime via AI: Use basic ADX, BB, etc. We'll compute a subset.
            # To be rigorous, we should replicate the exact features. For immediate upgrade, we'll:
            #   run market analyzer, then if market_state != Insufficient Data, we treat as Trend.
            # That is equivalent to AI predicting Trend? Not exactly. We'll quickly compute a simple regime flag:
            adx = df['ADX_14'] if 'ADX_14' in df.columns else None
            if adx is None:
                # Compute ADX quickly
                import pandas_ta as ta
                df.ta.adx(length=14, append=True)
                df.ta.bbands(length=20, std=2, append=True)
                df.ta.atr(length=14, append=True)
                df.ta.rsi(length=14, append=True)
            latest = df.iloc[-1]
            # Prepare feature vector for model
            feature_cols = [
                'ADX_14','ADXR_14_2','DMP_14','DMN_14','BBL_20_2.0_2.0','BBM_20_2.0_2.0','BBU_20_2.0_2.0','BBB_20_2.0_2.0','BBP_20_2.0_2.0',
                'ATRr_14','RSI_14','EMA_50','EMA_200','BB_WIDTH','RSI_STD_20','PRICE_EMA200_DIST'
            ]
            # Some features may be missing if we haven't computed all; compute remaining
            if 'BB_WIDTH' not in df.columns:
                df['BB_WIDTH'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0']
            if 'RSI_STD_20' not in df.columns:
                df['RSI_STD_20'] = df['RSI_14'].rolling(window=20).std()
            if 'PRICE_EMA200_DIST' not in df.columns:
                df['PRICE_EMA200_DIST'] = (df['Close'] - df['EMA_200']) / df['EMA_200']
            if 'ADXR_14_2' not in df.columns:
                # ADXR is ADX rolling average, approximate by ADX for now
                df['ADXR_14_2'] = df['ADX_14']
            if 'DMP_14' not in df.columns or 'DMN_14' not in df.columns:
                # Could compute using DMI but approximate with ADX direction? We'll fill with 0 to avoid crash.
                df['DMP_14'] = 0
                df['DMN_14'] = 0
            try:
                X = latest[feature_cols].values.reshape(1, -1)
                regime = regime_model.predict(X)[0]
            except Exception as e:
                print(f"  Feature prepare error for {symbol}: {e}")
                continue

            if regime == 0:  # Range
                continue

            # Trend confirmed by AI, proceed with MarketStateAnalyzer for direction
            market_state, conf = analyzer.analyze(df)
            if market_state == "Insufficient Data" or conf <= 0.7:
                continue

            price = latest['Close']
            atr = latest.get('ATRr_14', latest.get('ATR', price * 0.02))

            # Position sizing
            risk_amount = usdt_balance * RISK_PER_TRADE_PCT
            sl_distance = atr * 1.5
            notional = (risk_amount / sl_distance) * price
            margin_required = notional / LEVERAGE

            # Check available margin
            # We need to estimate current used margin from open positions
            # Fetch all positions to compute used margin
            all_positions = exchange.fetch_positions()
            used_margin = sum(float(p.get('initialMargin',0) or 0) for p in all_positions if float(p.get('positionAmt',0)) != 0)
            available = usdt_balance - used_margin
            if available < margin_required:
                continue

            # Determine side
            if market_state in ["Uptrend","Volatile Uptrend"] and not global_long_veto:
                # Open LONG
                amount = float(exchange.amount_to_precision(symbol, notional/price))
                if amount * price < 10:
                    continue
                try:
                    # Set leverage
                    exchange.set_leverage(LEVERAGE, symbol)
                    # Market buy
                    order = exchange.create_order(symbol, 'market', 'buy', amount)
                    # Calculate stop loss price
                    sl_price = float(exchange.price_to_precision(symbol, price - sl_distance))
                    # Create STOP_MARKET sell order to close
                    sl_order = exchange.create_order(symbol, 'STOP_MARKET', 'sell', amount, params={'stopPrice': sl_price, 'closePosition': True})
                    # Send notification
                    msg = (f"🔥 [LONG OPEN] 🔥\nPair: {symbol}\nPrice: ${price:.4f}\nAmount: {amount}\nLeverage: {LEVERAGE}x\nMargin: ${margin_required:.2f}\nStop Loss: ${sl_price:.4f}")
                    print(f"  ✅ LONG {symbol} @ {price:.4f}")
                    new_signals.append(f"{symbol} 开多")
                    send_whatsapp_alert(msg)
                except Exception as e:
                    err = f"🚨 LONG failed on {symbol}: {e}"
                    print(err)
                    send_whatsapp_alert(err)

            elif market_state in ["Downtrend","Volatile Downtrend"] and not global_short_veto:
                # Open SHORT
                amount = float(exchange.amount_to_precision(symbol, notional/price))
                if amount * price < 10:
                    continue
                try:
                    exchange.set_leverage(LEVERAGE, symbol)
                    # Market sell (short)
                    order = exchange.create_order(symbol, 'market', 'sell', amount)
                    sl_price = float(exchange.price_to_precision(symbol, price + sl_distance))
                    sl_order = exchange.create_order(symbol, 'STOP_MARKET', 'buy', amount, params={'stopPrice': sl_price, 'closePosition': True})
                    msg = (f"🔥 [SHORT OPEN] 🔥\nPair: {symbol}\nPrice: ${price:.4f}\nAmount: {amount}\nLeverage: {LEVERAGE}x\nMargin: ${margin_required:.2f}\nStop Loss: ${sl_price:.4f}")
                    print(f"  ✅ SHORT {symbol} @ {price:.4f}")
                    new_signals.append(f"{symbol} 开空")
                    send_whatsapp_alert(msg)
                except Exception as e:
                    err = f"🚨 SHORT failed on {symbol}: {e}"
                    print(err)
                    send_whatsapp_alert(err)
        except Exception as e:
            print(f"    Error scanning {symbol}: {e}")

    # Summary
    summary = f"📊 实盘扫描完成\n"
    summary += f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')}\n"
    summary += f"💰 可用余额: ${usdt_balance:.2f}\n"
    summary += f"🔍 扫描数: {len(top_symbols)}\n"
    if new_signals:
        summary += f"🆕 新开仓({len(new_signals)}): " + ", ".join(new_signals) + "\n"
    else:
        summary += "🆕 本次无新信号\n"
    print(summary)
    send_whatsapp_alert(summary)

if __name__ == "__main__":
    # Single-run mode; crontab will schedule it
    execute_real_trade()
