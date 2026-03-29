"""
改进版三分类标签：使用分位数阈值（适应不同波动）
"""

import pandas as pd
import numpy as np

def label_data_3class_quantile(df, look_forward_candles=24, quantile_threshold=0.6):
    """
    使用动态分位数阈值定义“强趋势”
    - 计算未来 N 根K线的最高/最低价格
    - 计算收益率（相对当前收盘价）
    - 取历史滚动窗口的80%分位数作为阈值
    - 条件：
      - 强上涨：未来最高涨幅 > 阈值 且 +DI>-DI 且 ADX>25
      - 强下跌：未来最低跌幅 > 阈值 且 -DI>+DI 且 ADX>25
      - 震荡：其他
    """
    # 未来N根K线的最高最低（修复：直接取未来价格，避免标签泄漏）
    future_high = df['High'].shift(-look_forward_candles)
    future_low = df['Low'].shift(-look_forward_candles)
    
    # 预期收益率
    up_return = (future_high - df['Close']) / df['Close']
    down_return = (df['Close'] - future_low) / df['Close']

    # 滚动分位数阈值（使用60个样本窗口 ≈ 60小时）
    window = 60
    up_thresh = up_return.rolling(window).quantile(quantile_threshold)
    down_thresh = down_return.rolling(window).quantile(quantile_threshold)

    # 方向 + ADX 条件
    plus_gt_minus = df['+DI'] > df['-DI']
    minus_gt_plus = df['-DI'] > df['+DI']
    adx_strong = df['ADX'] >= 23

    cond_up = (up_return > up_thresh) & plus_gt_minus & adx_strong
    cond_down = (down_return > down_thresh) & minus_gt_plus & adx_strong

    df['regime'] = 1  # 震荡
    df.loc[cond_up, 'regime'] = 2   # 强涨
    df.loc[cond_down, 'regime'] = 0  # 强跌

    df.dropna(subset=['regime'], inplace=True)
    return df

def prepare_features_v2(df):
    """特征工程（包含多时间框架和统计特征）"""
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # --- 基础指标（1h）---
    df['EMA_50'] = calculate_ema(close, 50)
    df['EMA_200'] = calculate_ema(close, 200)
    df['ADX'], df['+DI'], df['-DI'] = calculate_adx(high, low, close, 14)
    df['ATR'] = calculate_atr(high, low, close, 14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = calculate_macd(close)
    df['RSI'] = calculate_rsi(close, 14)

    # --- 方向特征 ---
    # 避免除零和inf
    ema200_safe = df['EMA_200'].replace(0, np.nan)
    df['Price_vs_EMA200'] = (close - ema200_safe) / ema200_safe
    df['Volume_Change_Ratio'] = volume.pct_change(5)
    df['DI_diff'] = df['+DI'] - df['-DI']

    # --- 交叉信号 ---
    df['+DI_cross_above_-DI'] = ((df['DI_diff'] > 0) & (df['DI_diff'].shift(1) <= 0)).astype(int)
    df['-DI_cross_above_+DI'] = ((df['DI_diff'] < 0) & (df['DI_diff'].shift(1) >= 0)).astype(int)

    # --- MACD动量 ---
    df['MACD_hist_positive'] = (df['MACD_hist'] > 0).astype(int)
    df['MACD_hist_cross_up'] = ((df['MACD_hist'] > 0) & (df['MACD_hist'].shift(1) <= 0)).astype(int)

    # --- 统计特征（滚动）---
    # 价格滚动波动率（20周期标准差） - 处理除零
    price_std = close.rolling(20).std()
    df['Price_std_20'] = price_std / close.replace(0, np.nan)

    # ATR相对波动率（ATR/Price） - 处理除零
    df['ATR_ratio'] = df['ATR'] / close.replace(0, np.nan)

    # 最大回撤（最近20根K线）
    rolling_max = close.rolling(20).max()
    df['Drawdown_20'] = (close - rolling_max) / rolling_max.replace(0, np.nan)

    # RSI偏离（当前RSI - 中位值50）
    df['RSI_dev'] = df['RSI'] - 50

    # --- 趋势强度标记 ---
    df['ADX_strong'] = (df['ADX'] >= 25).astype(int)
    df['ADX_weak'] = (df['ADX'] <= 20).astype(int)

    # 替换inf为NaN然后drop
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    return df

# 复制原计算函数...
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

# ========================
# 配置常量（供 paper_trader_v2.py 导入）
# ========================
ADX_STRONG_THRESHOLD = 22
ADX_WEAK_THRESHOLD = 20
CONFIDENCE_THRESHOLD = 0.55
LEVERAGE = 2.5
RISK_PER_TRADE_PCT = 0.08
STOP_LOSS_ATR_MULT = 2.0
TAKE_PROFIT_RR = 2.0
TRAILING_STOP_ATR = 1.5
