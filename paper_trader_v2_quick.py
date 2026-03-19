"""
快速验证版：用规则判断方向（无需训练模型）
测试三分类逻辑是否正确识别涨跌趋势
"""

import os, json, datetime, time, ccxt, pandas as pd
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
ADX_STRONG_THRESHOLD = 25
ADX_WEAK_THRESHOLD = 20
STATE_FILE = 'paper_trade_state.json'
LEVERAGE = 2.5
RISK_PCT = 0.08
STOP_LOSS_ATR = 2.0
TAKE_PROFIT_RR = 2.0
DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'

# ----- 简化的特征计算函数（复制自strategy_v2）-----
def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_adx(high, low, close, period=14):
    if len(close) < period * 2:
        return pd.Series(np.nan, index=close.index), pd.Series(np.nan, index=close.index), pd.Series(np.nan, index=close.index)
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum.reduce([tr1, tr2, tr3])
    tr = pd.Series(tr, index=high.index)
    up_move = high.diff()
    down_move = low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)
    atr = calculate_ema(tr, period)
    plus_di = 100 * (calculate_ema(plus_dm, period) / atr)
    minus_di = 100 * (calculate_ema(minus_dm, period) / atr)
    di_sum = plus_di + minus_di
    dx = 100 * np.abs(plus_di - minus_di) / di_sum.replace(0, np.nan)
    adx = calculate_ema(dx, period)
    return adx, plus_di, minus_di

def calculate_macd(close, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum.reduce([tr1, tr2, tr3])
    tr = pd.Series(tr, index=high.index)
    return calculate_ema(tr, period)

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = calculate_ema(gain, period)
    avg_loss = calculate_ema(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_features(df):
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    df['EMA_50'] = calculate_ema(close, 50)
    df['EMA_200'] = calculate_ema(close, 200)
    df['ADX'], df['+DI'], df['-DI'] = calculate_adx(high, low, close, 14)
    df['ATR'] = calculate_atr(high, low, close, 14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = calculate_macd(close)
    df['RSI'] = calculate_rsi(close, 14)
    df['DI_diff'] = df['+DI'] - df['-DI']
    df.dropna(inplace=True)
    return df

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'balance': 10000.0, 'positions': {}, 'trade_history': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def send_whatsapp(msg):
    print(f"[WA] {msg}")
    if DRY_RUN:
        return
    # 实际发送逻辑...

def scan_and_quick():
    print(f"\n{'='*60}")
    print(f"🚀 Quick v2 Test - {datetime.datetime.now():%H:%M}")
    print(f"{'='*60}\n")

    state = load_state()
    balance = state['balance']
    positions = state['positions']
    exchange = ccxt.binance({'enableRateLimit': True})

    # Update positions
    closed = []
    for sym, pos in list(positions.items()):
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry, amt, atr, sl = pos['entry_price'], pos['amount'], pos['atr'], pos['sl']
            if pos['type'] == 'BUY':
                if price <= sl:
                    pnl = (sl - entry) * amt
                    balance += pos['margin'] + pnl
                    closed.append((sym, pnl))
                    print(f"  CLOSED LONG {sym} SL hit PnL:${pnl:.2f}")
            elif pos['type'] == 'SELL':
                if price >= sl:
                    pnl = (entry - sl) * amt
                    balance += pos['margin'] + pnl
                    closed.append((sym, pnl))
                    print(f"  CLOSED SHORT {sym} SL hit PnL:${pnl:.2f}")
        except Exception as e:
            print(f"  Error {sym}: {e}")

    for sym, pnl in closed:
        positions.pop(sym, None)
        state['trade_history'].append({'symbol':sym,'pnl':pnl,'exit_time':datetime.datetime.utcnow().isoformat()+'Z'})

    # Scan
    tickers = exchange.fetch_tickers()
    symbols = [s for s,t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
    symbols.sort(key=lambda s: tickers[s].get('quoteVolume',0), reverse=True)
    symbols = symbols[:50]

    new_entries = []

    for symbol in symbols:
        if symbol in positions:
            continue
        time.sleep(0.2)
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            if len(df) < 200:
                continue

            df = calculate_features(df)
            latest = df.iloc[-1]

            adx = latest['ADX']
            plus_di = latest['+DI']
            minus_di = latest['-DI']
            macd_hist = latest['MACD_hist']
            price = latest['Close']
            atr = latest['ATR']

            # 方向判断（规则代替模型）
            signal = None
            reason = ""

            if adx >= ADX_STRONG_THRESHOLD:
                if plus_di > minus_di and macd_hist > 0:
                    signal = "BUY"
                    reason = f"ADX={adx:.1f} +DI>{minus_di:.1f} MACD+{macd_hist:.4f}"
                elif minus_di > plus_di and macd_hist < 0:
                    signal = "SELL"
                    reason = f"ADX={adx:.1f} -DI>{plus_di:.1f} MACD{macd_hist:.4f}"
            elif adx <= ADX_WEAK_THRESHOLD:
                reason = f"ADX={adx:.1f} (震荡)"
                signal = "HOLD"

            if signal in ["BUY","SELL"]:
                # 仓位计算
                risk_amt = balance * RISK_PCT
                sl_price = price - atr*STOP_LOSS_ATR if signal=="BUY" else price + atr*STOP_LOSS_ATR
                tp_price = price + (price-sl_price)*TAKE_PROFIT_RR if signal=="BUY" else price - (sl_price-price)*TAKE_PROFIT_RR
                price_risk = abs(price - sl_price)
                if price_risk <= 0:
                    continue
                amt = risk_amt / price_risk
                max_notional = balance * LEVERAGE
                if amt * price > max_notional:
                    amt = max_notional / price
                margin = (amt * price) / LEVERAGE
                used = sum(p['margin'] for p in positions.values())
                if margin > (balance - used):
                    continue

                balance -= margin
                pos = {
                    'type': signal,
                    'entry_price': price,
                    'amount': amt,
                    'margin': margin,
                    'atr': atr,
                    'sl': sl_price,
                    'tp': tp_price,
                    'highest_seen': price if signal=="BUY" else None,
                    'lowest_seen': price if signal=="SELL" else None,
                    'entry_time': datetime.datetime.utcnow().isoformat()+'Z'
                }
                positions[symbol] = pos
                new_entries.append(f"{symbol} {signal} @{price:.4f} SL:{sl_price:.4f}")
                print(f"  NEW {signal} {symbol} @{price:.4f} ATR:{atr:.4f} margin:${margin:.2f}")

        except Exception as e:
            print(f"  Scan error {symbol}: {e}")

    # Summary
    total_equity = balance + sum(p['margin'] for p in positions.values())
    print(f"\n--- Summary ---")
    print(f"Equity: ${total_equity:.2f} ({((total_equity/10000)-1)*100:+.1f}%)")
    print(f"Closed: {len(closed)}")
    print(f"New: {len(new_entries)}")

    state['balance'] = balance
    state['positions'] = positions
    save_state(state)

if __name__ == '__main__':
    scan_and_quick()
