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
import shutil

# Workspace root for models and shared files
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Import custom modules
from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer
from regime_trader_ai_product.code.sentiment_handler import MacroSentimentHandler
from test_smart_money import get_binance_ls_ratio

load_dotenv()

LEVERAGE = 3
RISK_PER_TRADE_PCT = 0.05
SCAN_LIMIT = 40
DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'

def send_whatsapp_alert(message):
    print(f"[WhatsApp Alert] {message}")
    # In DRY_RUN mode, do not actually send messages
    if DRY_RUN:
        print("[WhatsApp] Dry-run: skip sending")
        return
    safe_msg = message.replace("'", "'\\''")
    target_number = "+8613908412393"
    # Use absolute path to openclaw CLI (crontab PATH may not include ~/.npm-global/bin)
    openclaw_path = "/home/sdrom2008/.npm-global/bin/openclaw"
    # Verify the executable exists
    if not os.path.exists(openclaw_path):
        print(f"[WhatsApp] Error: openclaw binary not found at {openclaw_path}")
        # Try to find it in PATH as fallback
        openclaw_path = shutil.which("openclaw") or "openclaw"
    cmd = f"'{openclaw_path}' message send --channel whatsapp --target '{target_number}' --message '{safe_msg}'"
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

    # Dry-run: execute a single paper_trader scan cycle and exit
    if DRY_RUN:
        print("🧪  DRY_RUN mode: executing paper_trader simulation cycle.")
        try:
            from regime_trader_ai_product.paper_trader import scan_and_trade
            scan_and_trade()
        except ImportError:
            from regime_trader_ai_product.paper_trader import run_paper_trader
            run_paper_trader()
        return

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
    model_path = os.path.join(workspace_root, 'regime_model.pkl')
    try:
        with open(model_path, 'rb') as f:
            regime_model = pickle.load(f)
        print("✅ AI Regime Model loaded.")
    except Exception as e:
        msg = f"❌ CRITICAL: Failed to load AI model - {e}"
        print(msg)
        send_whatsapp_alert(msg)
        return

    # Macro filters
    sentiment_label = "NEUTRAL"
    try:
        sentiment_handler = MacroSentimentHandler()
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
        exchange = get_exchange()
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
            df['ATR'] = df['High'] - df['Low']  # simplified stub; use pandas_ta.ATR for production

            # AI regime prediction
            # Compute the same 16 features as training
            import pandas_ta as ta
            df.ta.adx(length=14, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.atr(length=14, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=50, append=True)
            df['BB_WIDTH'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0']
            df['RSI_STD_20'] = df['RSI_14'].rolling(window=20).std()
            df['PRICE_EMA200_DIST'] = (df['Close'] - df['EMA_200']) / df['EMA_200']
            # ADXR and DMP/DMN approximations
            df['ADXR_14_2'] = df['ADX_14']
            df['DMP_14'] = 0
            df['DMN_14'] = 0
            df.dropna(inplace=True)
            if df.empty:
                continue
            latest = df.iloc[-1]
            feature_cols = [
                'ADX_14','ADXR_14_2','DMP_14','DMN_14','BBL_20_2.0_2.0','BBM_20_2.0_2.0','BBU_20_2.0_2.0','BBB_20_2.0_2.0','BBP_20_2.0_2.0',
                'ATRr_14','RSI_14','EMA_50','EMA_200','BB_WIDTH','RSI_STD_20','PRICE_EMA200_DIST'
            ]
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
            atr = latest['ATRr_14']

            # Position sizing
            risk_amount = usdt_balance * RISK_PER_TRADE_PCT
            sl_distance = atr * 1.5
            notional = (risk_amount / sl_distance) * price
            margin_required = notional / LEVERAGE

            # Check available margin
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
                msg = (f"🔥 [LONG {'DRY-RUN' if DRY_RUN else 'OPEN'}] 🔥\nPair: {symbol}\nPrice: ${price:.4f}\nAmount: {amount}\nLeverage: {LEVERAGE}x\nMargin: ${margin_required:.2f}\nStop Loss: ${price - sl_distance:.4f}")
                print(f"  ✅ LONG {symbol} @ {price:.4f} (dry_run={DRY_RUN})")
                new_signals.append(f"{symbol} 开多")
                if not DRY_RUN:
                    exchange.set_leverage(LEVERAGE, symbol)
                    order = exchange.create_order(symbol, 'market', 'buy', amount)
                    sl_price = float(exchange.price_to_precision(symbol, price - sl_distance))
                    sl_order = exchange.create_order(symbol, 'STOP_MARKET', 'sell', amount, params={'stopPrice': sl_price, 'closePosition': True})
                send_whatsapp_alert(msg)

            elif market_state in ["Downtrend","Volatile Downtrend"] and not global_short_veto:
                # Open SHORT
                amount = float(exchange.amount_to_precision(symbol, notional/price))
                if amount * price < 10:
                    continue
                msg = (f"🔥 [SHORT {'DRY-RUN' if DRY_RUN else 'OPEN'}] 🔥\nPair: {symbol}\nPrice: ${price:.4f}\nAmount: {amount}\nLeverage: {LEVERAGE}x\nMargin: ${margin_required:.2f}\nStop Loss: ${price + sl_distance:.4f}")
                print(f"  ✅ SHORT {symbol} @ {price:.4f} (dry_run={DRY_RUN})")
                new_signals.append(f"{symbol} 开空")
                if not DRY_RUN:
                    exchange.set_leverage(LEVERAGE, symbol)
                    order = exchange.create_order(symbol, 'market', 'sell', amount)
                    sl_price = float(exchange.price_to_precision(symbol, price + sl_distance))
                    sl_order = exchange.create_order(symbol, 'STOP_MARKET', 'buy', amount, params={'stopPrice': sl_price, 'closePosition': True})
                send_whatsapp_alert(msg)
        except Exception as e:
            print(f"    Error scanning {symbol}: {e}")

    summary = f"📊 实盘扫描完成\n"
    summary += f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')}\n"
    summary += f"💰 可用余额: ${usdt_balance:.2f}\n"
    summary += f"🔍 扫描数: {len(top_symbols)}\n"
    if new_signals:
        summary += f"🆕 新开仓({len(new_signals)}): " + ", ".join(new_signals) + "\n"
    else:
        summary += "🆕 本次无新信号\n"
    print(summary)
    # Send summary report only on the hour (e.g., 10:00, 11:00) to avoid spam
    now = datetime.datetime.now()
    if now.minute == 0:
        send_whatsapp_alert(summary)
    else:
        print("[Report] Not on the hour, skipping WhatsApp summary")

if __name__ == "__main__":
    # 支持 v2 策略切换（需先训练: python train_model_v2.py）
    if os.environ.get('STRATEGY_VERSION') == 'v2':
        print("[*] Using v2 strategy (3-class model)")
        from regime_trader_ai_product.paper_trader_v2 import scan_and_trade_v2
        scan_and_trade_v2()
    else:
        execute_real_trade()
