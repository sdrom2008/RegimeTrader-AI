import os
import json
import time
import datetime
import pandas as pd
import ccxt
from dotenv import load_dotenv
import pickle
import subprocess
import sys

# Ensure workspace root is on path for imports
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Import custom modules
from regime_trader_ai_product.code.market_state_logic import MarketStateAnalyzer
from test_smart_money import get_binance_ls_ratio
from ai_news_reader import fetch_crypto_rss

# pandas_ta
try:
    import pandas_ta as ta
except ImportError:
    print("[!] pandas_ta is not installed. Run: pip install pandas_ta")
    exit(1)

load_dotenv()

STATE_FILE = 'paper_trade_state.json'
LEVERAGE = 3.0
INITIAL_BALANCE = 10000.0  # 10,000 USDT
RISK_PER_TRADE_PCT = 0.05
SCAN_INTERVAL = 300  # 5 minutes
SCAN_LIMIT = 60  # number of top symbols to scan
MARKET_CONF_THRESHOLD = 0.7  # minimum confidence to enter

MODEL_FEATURES = [
    'ADX_14','ADXR_14_2','DMP_14','DMN_14','BBL_20_2.0_2.0',
    'BBM_20_2.0_2.0','BBU_20_2.0_2.0','BBB_20_2.0_2.0','BBP_20_2.0_2.0',
    'ATRr_14','RSI_14','EMA_50','EMA_200','BB_WIDTH','RSI_STD_20',
    'PRICE_EMA200_DIST'
]

def get_llm_news_sentiment():
    return "NEUTRAL", 0.5

def send_whatsapp_alert(message):
    print(f"[WhatsApp] {message}")
    safe_msg = message.replace("'", "'\\''")
    target = "+8613908412393"
    openclaw_path = "/home/sdrom2008/.npm-global/bin/openclaw"
    cmd = f"{openclaw_path} message send --channel whatsapp --target '{target}' --message '{safe_msg}'"
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"[WhatsApp] Sent")
    except Exception as e:
        print(f"[WhatsApp] Failed: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'balance': INITIAL_BALANCE, 'positions': {}, 'trade_history': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def calculate_features(df):
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

def scan_and_trade():
    print(f"\n{'='*60}")
    print(f"🚀 AI Regime Trader - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Load model
    try:
        with open('regime_model.pkl', 'rb') as f:
            regime_model = pickle.load(f)
    except Exception as e:
        print(f"❌ Model load failed: {e}")
        send_whatsapp_alert(f"❌ 模拟盘错误：模型加载失败 - {e}")
        return

    state = load_state()
    balance = state['balance']
    positions = state['positions']
    print(f"💰 余额: ${balance:.2f} | 持仓: {len(positions)}")

    fee_rate = 0.0004  # 0.04% per leg, total 0.08% round turn

    # Macro filters
    sentiment_label, _ = get_llm_news_sentiment()
    sm_data = get_binance_ls_ratio()
    sm_signal = "NEUTRAL"
    if sm_data:
        if sm_data.get('global_ls_ratio',1) > 1.5 and sm_data.get('top_position_ls_ratio',1) < 0.8:
            sm_signal = "BEARISH"
        elif sm_data.get('top_position_ls_ratio',1) > 1.3:
            sm_signal = "BULLISH"
    long_veto = (sentiment_label == "NEGATIVE") or (sm_signal == "BEARISH")
    short_veto = (sentiment_label == "POSITIVE") or False  # BULLISH not used for short veto yet

    exchange = ccxt.binance({'enableRateLimit': True})

    closed_positions = []
    unrealized_pnl_total = 0.0

    # 1) Update existing positions: mark to market, trailing stop, check stop hit
    for sym, pos in list(positions.items()):
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry = pos['entry_price']
            amt = pos['amount']
            atr = pos['atr']
            sl = pos['sl']

            if pos['type'] == 'BUY':
                # Update highest seen and trailing stop
                if price > pos.get('highest_seen', entry):
                    pos['highest_seen'] = price
                    new_sl = max(sl, price - atr*1.5)
                    pos['sl'] = new_sl
                # Check stop loss
                if price <= sl:
                    exit_price = sl
                    pnl = (exit_price - entry) * amt
                    fee = (exit_price * amt) * fee_rate * 2
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    print(f"  CLOSED LONG {sym} @{exit_price:.4f} PnL:${pnl:.2f} Fee:${fee:.2f} Returned margin:${pos['margin']:.2f}")
            elif pos['type'] == 'SELL':
                if price < pos.get('lowest_seen', entry):
                    pos['lowest_seen'] = price
                    new_sl = min(sl, price + atr*1.5)
                    pos['sl'] = new_sl
                if price >= sl:
                    exit_price = sl
                    pnl = (entry - exit_price) * amt
                    fee = (exit_price * amt) * fee_rate * 2
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    print(f"  CLOSED SHORT {sym} @{exit_price:.4f} PnL:${pnl:.2f} Fee:${fee:.2f} Returned margin:${pos['margin']:.2f}")
            else:
                continue

            # Compute unrealized P&L for this position (for reporting and available calc)
            if pos['type'] == 'BUY':
                unreal = (price - entry) * amt
            else:
                unreal = (entry - price) * amt
            unrealized_pnl_total += unreal

        except Exception as e:
            print(f"  Error updating {sym}: {e}")

    # Remove closed positions and record in history
    for sym, pnl, fee in closed_positions:
        positions.pop(sym, None)
        state['trade_history'].append({
            'symbol': sym,
            'pnl': pnl,
            'fee': fee,
            'exit_time': datetime.datetime.utcnow().isoformat()+'Z'
        })

    # 2) Compute total equity (balance + used margin + unrealized)
    margin_used = sum(p['margin'] for p in positions.values())
    total_equity = balance + margin_used + unrealized_pnl_total

    # 3) Scan for new opportunities
    new_signals = []
    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers()
        usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
        usdt_pairs.sort(key=lambda s: tickers[s].get('quoteVolume',0) or 0, reverse=True)
        top_symbols = usdt_pairs[:60]
    except Exception as e:
        print(f"  Failed to fetch tickers: {e}")
        top_symbols = []

    for symbol in top_symbols:
        if symbol in positions:
            continue
        time.sleep(0.2)
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            if len(df) < 200:
                continue
            df_feat = calculate_features(df.copy())
            if df_feat.empty:
                continue
            latest = df_feat.iloc[-1]
            features = latest[MODEL_FEATURES].values.reshape(1,-1)
            regime = regime_model.predict(features)[0]
            if regime == 0:  # RANGE
                continue
            # TREND
            analyzer = MarketStateAnalyzer()
            market_state, conf = analyzer.analyze(df)
            price = latest['Close']
            atr = latest['ATRr_14']
            risk_amount = total_equity * RISK_PER_TRADE_PCT
            notional = (risk_amount / (atr*1.5)) * price
            margin_req = notional / LEVERAGE

            # Check available margin: total_equity must cover sum(margin) + new margin
            used_margin = sum(p['margin'] for p in positions.values())
            available = total_equity - used_margin
            if available < margin_req:
                continue

            if market_state in ["Uptrend","Volatile Uptrend"] and conf >= 0.7 and not long_veto:
                amount = float(exchange.amount_to_precision(symbol, notional/price))
                if amount*price < 10:
                    continue
                # Deduct margin from balance immediately
                if balance < margin_req:
                    continue
                balance -= margin_req
                pos = {
                    'type':'BUY',
                    'entry_price':price,
                    'amount':amount,
                    'margin':margin_req,
                    'atr':atr,
                    'sl': price - atr*1.5,
                    'highest_seen':price,
                    'entry_time': datetime.datetime.utcnow().isoformat()+'Z'
                }
                positions[symbol] = pos
                new_signals.append(f"{symbol} 开多 @{price:.4f}")
                print(f"  📈 NEW LONG {symbol} @ {price:.4f} Margin:${margin_req:.2f} Cash left:${balance:.2f}")
            elif market_state in ["Downtrend","Volatile Downtrend"] and conf >= 0.7 and not short_veto:
                amount = float(exchange.amount_to_precision(symbol, notional/price))
                if amount*price < 10:
                    continue
                if balance < margin_req:
                    continue
                balance -= margin_req
                pos = {
                    'type':'SELL',
                    'entry_price':price,
                    'amount':amount,
                    'margin':margin_req,
                    'atr':atr,
                    'sl': price + atr*1.5,
                    'lowest_seen':price,
                    'entry_time': datetime.datetime.utcnow().isoformat()+'Z'
                }
                positions[symbol] = pos
                new_signals.append(f"{symbol} 开空 @{price:.4f}")
                print(f"  📉 NEW SHORT {symbol} @ {price:.4f} Margin:${margin_req:.2f} Cash left:${balance:.2f}")
        except Exception as e:
            pass  # skip errors

    # 4) Update state: balance may have changed from closures; positions updated
    state['balance'] = balance
    save_state(state)

    # 5) Compute final total equity for report (balance + margin + unrealized)
    margin_used2 = sum(p['margin'] for p in positions.values())
    final_unrealized = 0.0
    for sym, pos in positions.items():
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry = pos['entry_price']
            amt = pos['amount']
            if pos['type'] == 'BUY':
                unreal = (price - entry) * amt
            else:
                unreal = (entry - price) * amt
            final_unrealized += unreal
        except Exception:
            pass
    final_total_equity = balance + margin_used2 + final_unrealized

    # Build detailed summary
    summary = f"📊 模拟盘扫描完成\n"
    summary += f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    summary += f"💰 总资产: ${final_total_equity:.2f} (余额: ${balance:.2f})\n"
    summary += f"📦 持仓数: {len(positions)}\n"
    if positions:
        summary += "🔍 当前持仓:\n"
        for sym, pos in positions.items():
            try:
                cur_price = exchange.fetch_ticker(sym)['last']
                entry = pos['entry_price']
                amt = pos['amount']
                if pos['type'] == 'BUY':
                    unreal = (cur_price - entry) * amt
                else:
                    unreal = (entry - cur_price) * amt
                sl = pos['sl']
                summary += f"  {sym}: {pos['type']} 数量={amt:.0f} 开仓={entry:.4f} 当前={cur_price:.4f} 未实现盈亏=${unreal:.2f} 止损={sl:.4f}\n"
            except Exception:
                summary += f"  {sym}: {pos['type']} 数量={pos['amount']:.0f} 开仓={pos['entry_price']:.4f} (价格获取失败)\n"
    if closed_positions:
        summary += f"✅ 本次平仓({len(closed_positions)}):\n"
        for sym, pnl, fee in closed_positions:
            summary += f"  {sym}: 盈亏=${pnl:.2f} 手续费=${fee:.2f}\n"
    if new_signals:
        summary += f"🆕 新开仓({len(new_signals)}): " + ", ".join(new_signals) + "\n"
    else:
        summary += "🆕 本次扫描无新开仓\n"
    print(summary)

    # Send WhatsApp summary only on the hour to avoid spam
    now = datetime.datetime.now()
    if now.minute == 0:
        send_whatsapp_alert(summary)
    else:
        print("[Report] Not on the hour, skipping WhatsApp summary")

def main_loop():
    send_whatsapp_alert("🤖 模拟盘常驻进程已启动，每5分钟扫描一次")
    while True:
        try:
            scan_and_trade()
        except Exception as e:
            err = f"扫描异常: {e}"
            print(err)
            send_whatsapp_alert(err)
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main_loop()
