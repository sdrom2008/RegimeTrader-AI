"""
v2 策略常量与函数（独立版本，不含 sklearn 依赖）
"""

import numpy as np
import pandas as pd

# ========== 配置参数 ==========
ADX_STRONG_THRESHOLD = 25
ADX_WEAK_THRESHOLD = 20
CONFIDENCE_THRESHOLD = 0.65
LEVERAGE = 2.5
RISK_PER_TRADE_PCT = 0.08
STOP_LOSS_ATR_MULT = 2.0
TAKE_PROFIT_RR = 2.0
TRAILING_STOP_ATR = 1.5

# ========== 技术指标函数 ==========
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
    df['Price_vs_EMA200'] = (close - df['EMA_200']) / df['EMA_200']
    df['DI_diff'] = df['+DI'] - df['-DI']
    df['ADX_strong'] = (df['ADX'] >= ADX_STRONG_THRESHOLD).astype(int)
    df['ADX_weak'] = (df['ADX'] <= ADX_WEAK_THRESHOLD).astype(int)
    df['MACD_hist_positive'] = (df['MACD_hist'] > 0).astype(int)
    df['MACD_hist_cross_up'] = ((df['MACD_hist'] > 0) & (df['MACD_hist'].shift(1) <= 0)).astype(int)
    df['+DI_cross_above_-DI'] = ((df['DI_diff'] > 0) & (df['DI_diff'].shift(1) <= 0)).astype(int)
    df['-DI_cross_above_+DI'] = ((df['DI_diff'] < 0) & (df['DI_diff'].shift(1) >= 0)).astype(int)
    # 成交量变化率（5周期）
    df['Volume_Change_Ratio'] = volume.pct_change(5)
    df.dropna(inplace=True)
    return df

def get_feature_columns():
    return [
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
