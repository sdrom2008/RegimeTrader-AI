# RegimeTrader AI - 优化版策略代码
# 三分类模型 + 双向交易 + 动态风控
# 作者: 虾子 (2026-03-19)

import os
import json
import time
import datetime
import pandas as pd
import numpy as np
import ccxt
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

# ========================
# 配置参数
# ========================
LEVERAGE = 2.5  # 降低杠杆（原3x）
RISK_PER_TRADE_PCT = 0.08  # 单仓最大风险（总资金的8%）
STOP_LOSS_ATR_MULT = 2.0   # 止损: 2×ATR
TAKE_PROFIT_RR = 2.0       # 止盈: 2倍风险（盈亏比2:1）
TRAILING_STOP_ATR = 1.5    # 移动止损: 1.5×ATR
ADX_STRONG_THRESHOLD = 25  # ADX强趋势阈值
ADX_WEAK_THRESHOLD = 20    # ADX震荡阈值
CONFIDENCE_THRESHOLD = 0.65# 模型置信度阈值
SCAN_LIMIT = 60            # 扫描币种数量
MIN_VOLUME_RANK = 20       # 只交易成交量前20的币

# 资金费率过滤
FUNDING_RATE_THRESHOLD = 0.0005  # 0.05%
ENABLE_FUNDING_FILTER = True

# 文件路径
STATE_FILE = 'paper_trade_state.json'
MODEL_FILE = 'regime_model_v2.pkl'
DATA_DIR = 'data'

# ========================
# 工具函数
# ========================

def calculate_ema(series, period):
    """指数移动平均"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_adx(high, low, close, period=14):
    """计算ADX、+DI、-DI"""
    if len(close) < period * 2:
        return pd.Series(np.nan, index=close.index), pd.Series(np.nan, index=close.index), pd.Series(np.nan, index=close.index)

    # True Range
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum.reduce([tr1, tr2, tr3])
    tr = pd.Series(tr, index=high.index)

    # +DM, -DM
    up_move = high.diff()
    down_move = low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    # Smoothed
    atr = calculate_ema(tr, period)
    plus_di = 100 * (calculate_ema(plus_dm, period) / atr)
    minus_di = 100 * (calculate_ema(minus_dm, period) / atr)

    # DX
    di_sum = plus_di + minus_di
    dx = 100 * np.abs(plus_di - minus_di) / di_sum.replace(0, np.nan)
    adx = calculate_ema(dx, period)

    return adx, plus_di, minus_di

def calculate_macd(close, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_atr(high, low, close, period=14):
    """ATR"""
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    tr = np.maximum.reduce([tr1, tr2, tr3])
    tr = pd.Series(tr, index=high.index)
    return calculate_ema(tr, period)

# ========================
# 数据加载与特征工程
# ========================

def load_historical_data(symbol, timeframe='1h', limit=500):
    """从Binance加载历史K线"""
    exchange = ccxt.binance({'enableRateLimit': True})
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_features(df):
    """计算所有特征"""
    # 基础价格数据
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # 技术指标
    df['EMA_50'] = calculate_ema(close, 50)
    df['EMA_200'] = calculate_ema(close, 200)
    df['ADX'], df['+DI'], df['-DI'] = calculate_adx(high, low, close, 14)
    df['ATR'] = calculate_atr(high, low, close, 14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = calculate_macd(close)
    df['RSI'] = calculate_rsi(close, 14)

    # 方向特征
    df['Price_vs_EMA200'] = (close - df['EMA_200']) / df['EMA_200']  # 价格相对200EMA
    df['Volume_Change_Ratio'] = volume.pct_change(5)  # 5周期成交量变化率
    df['DI_diff'] = df['+DI'] - df['-DI']  # DI差值

    # 交叉信号
    df['+DI_cross_above_-DI'] = ((df['DI_diff'] > 0) & (df['DI_diff'].shift(1) <= 0)).astype(int)
    df['-DI_cross_above_+DI'] = ((df['DI_diff'] < 0) & (df['DI_diff'].shift(1) >= 0)).astype(int)

    # MACD动量
    df['MACD_hist_positive'] = (df['MACD_hist'] > 0).astype(int)
    df['MACD_hist_cross_up'] = ((df['MACD_hist'] > 0) & (df['MACD_hist'].shift(1) <= 0)).astype(int)

    # 趋势强度
    df['ADX_strong'] = (df['ADX'] >= ADX_STRONG_THRESHOLD).astype(int)
    df['ADX_weak'] = (df['ADX'] <= ADX_WEAK_THRESHOLD).astype(int)

    df.dropna(inplace=True)
    return df

def calculate_rsi(close, period=14):
    """RSI计算"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = calculate_ema(gain, period)
    avg_loss = calculate_ema(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

# ========================
# 三分类标签生成
# ========================

def label_data_3class(df, look_forward_candles=24, atr_multiplier=2.0, adx_threshold=25):
    """
    三分类标签：
    2: Strong Up (未来涨幅 > ATR×multiplier 且 ADX > threshold)
    0: Strong Down (未来跌幅 > ATR×multiplier 且 ADX > threshold)
    1: Oscillation (震荡/无法判断)
    """
    # 未来价格范围
    future_high = df['High'].shift(-look_forward_candles).rolling(window=look_forward_candles).max()
    future_low = df['Low'].shift(-look_forward_candles).rolling(window=look_forward_candles).min()
    future_close = df['Close'].shift(-look_forward_candles)

    # 预期价格变化
    price_change_up = (future_high - df['Close']) / df['Close']
    price_change_down = (df['Close'] - future_low) / df['Close']

    # ATR阈值
    threshold = df['ATR'] / df['Close'] * atr_multiplier

    # ADX条件
    adx_strong = df['ADX'] >= adx_threshold
    plus_di_gt_minus = df['+DI'] > df['-DI']
    minus_di_gt_plus = df['-DI'] > df['+DI']

    # 条件组合
    condition_up = adx_strong & plus_di_gt_minus & (price_change_up > threshold)
    condition_down = adx_strong & minus_di_gt_plus & (price_change_down > threshold)

    df['regime'] = 1  # 默认为震荡
    df.loc[condition_up, 'regime'] = 2   # 强上涨
    df.loc[condition_down, 'regime'] = 0  # 强下跌

    # 去掉未来数据不可用的行
    df.dropna(subset=['regime'], inplace=True)
    return df

# ========================
# 模型训练
# ========================

def train_model_3class(features_file='data/BTC_USDT_1h_2y_features.csv'):
    """训练三分类模型"""
    print("[*] Loading data...")
    df = pd.read_csv(features_file, index_col='timestamp', parse_dates=True)

    print("[*] Calculating features and labels...")
    df = calculate_features(df)
    df = label_data_3class(df)

    # 特征列表（包含方向特征）
    feature_cols = [
        'ADX', '+DI', '-DI', 'DI_diff',
        'MACD_hist', 'MACD_hist_cross_up',
        'RSI', 'ATR',
        'Price_vs_EMA200',
        'Volume_Change_Ratio',
        'EMA_50', 'EMA_200',
        'ADX_strong', 'ADX_weak',
        '+DI_cross_above_-DI', '-DI_cross_above_+DI',
        'MACD_hist_positive'
    ]

    X = df[feature_cols]
    y = df['regime']

    print(f"[*] Total samples: {len(X)}")
    print(f"[*] Class distribution:\n{y.value_counts().sort_index()}")
    print(f"[*] Class proportion:\n{y.value_counts(normalize=True).sort_index()}")

    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"[*] Training on {len(X_train)} samples, testing on {len(X_test)}")

    # 训练模型
    print("[*] Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # 评估
    y_pred = model.predict(X_test)
    print("\n=== Model Evaluation ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Down (0)', 'Osc (1)', 'Up (2)']))

    # 特征重要性
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\nTop Features:")
    print(importances.head(15))

    # 保存模型
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n[+] Model saved to {MODEL_FILE}")

    return model, feature_cols

# ========================
# 信号生成逻辑
# ========================

def generate_signals(df, model, feature_cols):
    """为最新数据生成交易信号"""
    signals = []

    # 确保所有特征存在
    for col in feature_cols:
        if col not in df.columns:
            raise ValueError(f"Missing feature: {col}")

    latest = df.iloc[-1]
    features = latest[feature_cols].values.reshape(1, -1)

    # 预测概率
    probs = model.predict_proba(features)[0]
    pred_class = model.predict(features)[0]
    confidence = probs[pred_class]

    # 条件判断
    adx = latest['ADX']
    plus_di = latest['+DI']
    minus_di = latest['-DI']
    macd_hist = latest['MACD_hist']
    price_vs_ema200 = latest['Price_vs_EMA200']

    signal = None
    reason = ""

    # 强趋势条件
    if adx >= ADX_STRONG_THRESHOLD:
        if plus_di > minus_di and macd_hist > 0 and confidence >= CONFIDENCE_THRESHOLD:
            if pred_class == 2:  # Up
                signal = "BUY"
                reason = f"ADX={adx:.1f}, +DI>{minus_di:.1f}, MACD_hist>0, conf={confidence:.2f}"
        elif minus_di > plus_di and macd_hist < 0 and confidence >= CONFIDENCE_THRESHOLD:
            if pred_class == 0:  # Down
                signal = "SELL"
                reason = f"ADX={adx:.1f}, -DI>{plus_di:.1f}, MACD_hist<0, conf={confidence:.2f}"

    # 震荡过滤
    if adx <= ADX_WEAK_THRESHOLD:
        reason = f"ADX={adx:.1f} < {ADX_WEAK_THRESHOLD} (震荡), 不开仓"
        signal = "HOLD"

    return {
        'signal': signal,
        'confidence': confidence,
        'predicted_class': int(pred_class),
        'adx': adx,
        'reason': reason,
        'features': {
            'plus_di': plus_di,
            'minus_di': minus_di,
            'macd_hist': macd_hist,
            'price_vs_ema200': price_vs_ema200
        }
    }

# ========================
# 风险管理
# ========================

def calculate_position_size(balance, entry_price, stop_loss_price, atr):
    """计算仓位大小（基于风险）"""
    risk_amount = balance * RISK_PER_TRADE_PCT  # 单笔风险金额
    price_risk = abs(entry_price - stop_loss_price)
    if price_risk == 0:
        return 0, 0

    # 基础数量 = 风险金额 / 价格风险
    amount = risk_amount / price_risk

    # 检查最大杠杆限制
    position_notional = amount * entry_price
    max_notional = balance * LEVERAGE
    if position_notional > max_notional:
        amount = max_notional / entry_price

    # 最小交易单位检查（Binance 合约精度）
    amount = max(amount, 0.001)  # 最小0.001

    margin_required = (amount * entry_price) / LEVERAGE
    return amount, margin_required

def get_funding_rate(symbol):
    """获取当前资金费率（模拟）"""
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        # 注意：需要交易所API权限
        # funding = exchange.fetch_funding_rate(symbol)
        # return funding['fundingRate']
        return 0.0  # 模拟返回
    except:
        return 0.0

def check_funding_filter(current_position, funding_rate):
    """资金费率过滤"""
    if not ENABLE_FUNDING_FILTER:
        return True, ""

    if current_position == "BUY" and funding_rate > FUNDING_RATE_THRESHOLD:
        return False, f"多头资金费过高: {funding_rate:.4%} > {FUNDING_RATE_THRESHOLD:.4%}"
    if current_position == "SELL" and funding_rate < -FUNDING_RATE_THRESHOLD:
        return False, f"空头资金费过高: {funding_rate:.4%} < {-FUNDING_RATE_THRESHOLD:.4%}"

    return True, ""

# ========================
# 核心交易逻辑
# ========================

def scan_and_trade():
    """主扫描交易函数"""
    print(f"\n{'='*60}")
    print(f"🚀 RegimeTrader AI v2.0 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. 加载模型
    try:
        with open(MODEL_FILE, 'rb') as f:
            model = pickle.load(f)
        print(f"[+] Model loaded: {MODEL_FILE}")
    except Exception as e:
        print(f"[!] Model load failed: {e}")
        return

    # 2. 加载状态
    state = load_state()
    balance = state['balance']
    positions = state['positions']
    print(f"[*] Balance: ${balance:.2f} | Positions: {len(positions)}")

    fee_rate = 0.0004  # 0.08%  round turn

    # 3. 更新现有持仓
    closed_positions = []
    unrealized_pnl_total = 0.0

    exchange = ccxt.binance({'enableRateLimit': True})

    for sym, pos in list(positions.items()):
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry = pos['entry_price']
            amount = pos['amount']
            atr = pos['atr']
            sl = pos['sl']

            # 计算未实现盈亏
            if pos['type'] == 'BUY':
                unreal = (price - entry) * amount
                unrealized_pnl_total += unreal

                # 移动止损（做多）
                if price > pos.get('highest_seen', entry):
                    pos['highest_seen'] = price
                    new_sl = max(sl, price - atr * TRAILING_STOP_ATR)
                    pos['sl'] = new_sl

                # 检查止损
                if price <= sl:
                    exit_price = sl
                    pnl = (exit_price - entry) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    print(f"  🔴 CLOSED LONG {sym} @{exit_price:.4f} PnL:${pnl:.2f}")

                    # 资金平仓后检查（如果因funding止损）
                    if 'funding_exit' in pos:
                        print(f"     Reason: Funding rate filter")

            elif pos['type'] == 'SELL':
                unreal = (entry - price) * amount
                unrealized_pnl_total += unreal

                if price < pos.get('lowest_seen', entry):
                    pos['lowest_seen'] = price
                    new_sl = min(sl, price + atr * TRAILING_STOP_ATR)
                    pos['sl'] = new_sl

                if price >= sl:
                    exit_price = sl
                    pnl = (entry - exit_price) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    print(f"  🔴 CLOSED SHORT {sym} @{exit_price:.4f} PnL:${pnl:.2f}")

        except Exception as e:
            print(f"  [!] Error updating {sym}: {e}")

    # 移除已平仓
    for sym, pnl, fee in closed_positions:
        positions.pop(sym, None)
        state['trade_history'].append({
            'symbol': sym,
            'pnl': pnl,
            'fee': fee,
            'exit_time': datetime.datetime.utcnow().isoformat()+'Z',
            'exit_reason': 'stop_loss'  # 可扩展
        })

    # 4. 计算总权益和可用保证金
    margin_used = sum(p['margin'] for p in positions.values())
    total_equity = balance + margin_used + unrealized_pnl_total

    print(f"[*] Total Equity: ${total_equity:.2f} | Cash: ${balance:.2f} | Margin Used: ${margin_used:.2f}")

    # 5. 扫描新机会
    print("[*] Scanning for new signals...")

    # 获取高流动性币种（成交量前60）
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
        usdt_pairs.sort(key=lambda s: tickers[s].get('quoteVolume',0) or 0, reverse=True)
        top_symbols = usdt_pairs[:SCAN_LIMIT]
    except Exception as e:
        print(f"[!] Failed to fetch tickers: {e}")
        top_symbols = []

    new_entries = []

    for symbol in top_symbols:
        if symbol in positions:
            continue

        time.sleep(0.2)  # API限流

        try:
            # 加载1小时间隔250根K线
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            if len(df) < 200:
                continue

            # 计算特征
            df_feat = calculate_features(df.copy())
            if df_feat.empty:
                continue

            # 生成信号
            signal_info = generate_signals(df_feat, model, MODEL_FILE.replace('_model.pkl','_features.csv').split('/')[-1])
            signal = signal_info['signal']
            confidence = signal_info['confidence']
            adx = signal_info['adx']
            reason = signal_info['reason']

            # 资金费率过滤
            funding_rate = get_funding_rate(symbol)
            funding_ok, funding_reason = check_funding_filter(signal, funding_rate)
            if not funding_ok:
                print(f"  [FUNDING] {symbol}: {funding_reason}")
                continue

            if signal in ["BUY", "SELL"] and confidence >= CONFIDENCE_THRESHOLD:
                latest = df_feat.iloc[-1]
                entry_price = latest['Close']
                atr = latest['ATR']

                # 计算止损价和仓位
                if signal == "BUY":
                    stop_loss_price = entry_price - atr * STOP_LOSS_ATR_MULT
                    take_profit_price = entry_price + (abs(entry_price - stop_loss_price) * TAKE_PROFIT_RR)
                else:  # SELL
                    stop_loss_price = entry_price + atr * STOP_LOSS_ATR_MULT
                    take_profit_price = entry_price - (abs(entry_price - stop_loss_price) * TAKE_PROFIT_RR)

                amount, margin_req = calculate_position_size(
                    total_equity, entry_price, stop_loss_price, atr
                )

                # 检查可用保证金
                used_margin = sum(p['margin'] for p in positions.values())
                available = total_equity - used_margin
                if margin_req > available:
                    print(f"  [!] Insufficient margin for {symbol}: need ${margin_req:.2f}, available ${available:.2f}")
                    continue

                # 开仓
                balance -= margin_req
                pos = {
                    'type': signal,
                    'entry_price': entry_price,
                    'amount': amount,
                    'margin': margin_req,
                    'atr': atr,
                    'sl': stop_loss_price,
                    'tp': take_profit_price,
                    'highest_seen': entry_price if signal=="BUY" else None,
                    'lowest_seen': entry_price if signal=="SELL" else None,
                    'entry_time': datetime.datetime.utcnow().isoformat()+'Z',
                    'confidence': confidence,
                    'adx': adx
                }
                positions[symbol] = pos
                new_entries.append(f"{symbol} {signal} @{entry_price:.4f} SL:{stop_loss_price:.4f} TP:{take_profit_price:.4f} Margin:${margin_req:.2f}")
                print(f"  📈 NEW {signal} {symbol} @{entry_price:.4f} | ATR:{atr:.4f} | Margin:${margin_req:.2f} | Conf:{confidence:.2f}")

        except Exception as e:
            print(f"  [!] Error scanning {symbol}: {e}")

    # 6. 保存状态
    state['balance'] = balance
    state['positions'] = positions
    save_state(state)

    # 7. 输出摘要
    print(f"\n--- Summary ---")
    print(f"Equity: ${total_equity:.2f} ({((total_equity/10000)-1)*100:+.1f}%)")
    print(f"Closed this cycle: {len(closed_positions)}")
    for sym, pnl, fee in closed_positions:
        print(f"  {sym}: ${pnl:+.2f}")
    print(f"New entries: {len(new_entries)}")
    for e in new_entries:
        print(f"  {e}")

# ========================
# 状态管理
# ========================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'balance': 10000.0, 'positions': {}, 'trade_history': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# ========================
# 主入口
# ========================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--train':
        print("🔥 Training 3-Class Regime Model...")
        train_model_3class()
    else:
        scan_and_trade()
