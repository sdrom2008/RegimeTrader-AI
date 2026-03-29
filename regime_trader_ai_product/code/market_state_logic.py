# market_state_logic.py
# This module handles the logic for identifying different market states and calculating a confidence score.

import pandas as pd
import numpy as np

# --- Helper functions for indicators (simplified for demonstration) ---
# In a real scenario, these would be robustly implemented or imported from a library.

def calculate_ema(data_series, period):
    if len(data_series) < period:
        return np.nan
    return data_series.ewm(span=period, adjust=False).mean()

def calculate_adx(high, low, close, period=14):
    if len(close) < period * 2: # ADX needs more data for DI calculations
        return np.nan

    # Calculate Directional Movement Index (DMI)
    # Simplified implementation for ADX calculation
    # A proper ADX calculation involves True Range, +DI, -DI, and smoothed values.
    
    # Calculate High-Low, High-Close, Low-Close differences for DMI calculation
    up_move = high.diff()
    down_move = low.diff()

    # Calculate +DM and -DM
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smoothed +DM and -DM (using Wilder's smoothing or simple moving average for demo)
    # Wilder's smoothing: SMMA(period) = (Previous SMMA * (period - 1) + Current Value) / period
    # For simplicity, using EMA for smoothing here.
    plus_di = calculate_ema(pd.Series(plus_dm), period)
    minus_di = calculate_ema(pd.Series(minus_dm), period)

    # Calculate Directional Indicators (+DI, -DI)
    tr = high - low
    # Add handling for period when tr could be zero or very small
    # TR = np.maximum(tr, (high - close.shift(1)).abs(), (low - close.shift(1)).abs())
    # For simplicity, let's use a basic form of TR (High-Low)
    TR = high - low
    TR_smoothed = calculate_ema(TR, period)

    plus_di_over_tr = (plus_di / TR_smoothed)
    minus_di_over_tr = (minus_di / TR_smoothed)

    # Calculate DI+/DI- ratio
    di_ratio = np.abs(plus_di_over_tr - minus_di_over_tr)
    di_sum = plus_di_over_tr + minus_di_over_tr

    # Calculate Directional Movement Index (DX)
    # Handle cases where di_sum is zero to avoid division by zero.
    dx = np.where(di_sum == 0, 0, (di_ratio / di_sum) * 100)

    # Calculate Average Directional Index (ADX) - smoothed DX
    adx = calculate_ema(pd.Series(dx), period)

    return adx

def calculate_macd(data_series, fast_period=12, slow_period=26, signal_period=9):
    if len(data_series) < slow_period + signal_period:
        return pd.Series(np.nan, index=data_series.index), pd.Series(np.nan, index=data_series.index), pd.Series(np.nan, index=data_series.index)
    
    ema_fast = calculate_ema(data_series, fast_period)
    ema_slow = calculate_ema(data_series, slow_period)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal_period)
    macd_histogram = macd_line - signal_line
    
    return macd_line, signal_line, macd_histogram

def calculate_rsi(data_series, period=14):
    delta = data_series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(high, low, close, period=14):
    # Ensure data series are of sufficient length for calculation
    if len(close) < period:
        return pd.Series(np.nan, index=high.index)
    
    # Calculate True Range (TR) using the Series directly
    tr1 = high - low
    tr2 = np.abs(high - close.shift(1))
    tr3 = np.abs(low - close.shift(1))
    # true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    # Correcting the usage of Series to calculate true_range
    true_range = np.maximum.reduce([tr1, tr2, tr3], axis=0)
    true_range = pd.Series(true_range, index=high.index) # Ensure it's a Series with correct index

    # Use EMA for smoothing TR to get ATR. EMA is common for ATR calculation.
    atr = calculate_ema(true_range, period)
    return atr

# --- Main Market State Analyzer Class ---

class MarketStateAnalyzer:
    def __init__(self, ema_short_period=12, ema_long_period=26, adx_period=14, atr_period=14):
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.market_state = None
        self.confidence_score = None
        
        # Thresholds for ADX and ATR to define market states
        self.adx_strong_trend_threshold = 30 # ADX > 30 indicates a strong trend
        self.adx_moderate_trend_threshold = 20 # ADX between 20-30 indicates a moderate trend
        # ADX < 20 suggests a weak trend or ranging market
        
        # ATR thresholds will be relative to price, so dynamic calculation is needed.
        # For simplicity, we'll use a factor based on recent ATR.

        # Thresholds for MACD histogram (simplified)
        self.macd_hist_positive_threshold = 0 # Above zero indicates bullish momentum
        self.macd_hist_negative_threshold = 0 # Below zero indicates bearish momentum

        # Confidence score weights (can be tuned)
        self.trend_strength_weight = 0.4
        self.trend_direction_weight = 0.3
        self.volatility_weight = 0.2
        self.mac_weight = 0.1 # Placeholder for other factors like MACD, or sentiment

    def analyze(self, data):
        # Ensure data is a pandas DataFrame and has OHLCV columns + Volume
        if not isinstance(data, pd.DataFrame) or not all(col in data.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
            raise ValueError("Input data must be a pandas DataFrame with OHLCV columns.")

        # Calculate necessary indicators if not already present
        if 'EMA_short' not in data.columns:
            data['EMA_short'] = calculate_ema(data['Close'], self.ema_short_period)
        if 'EMA_long' not in data.columns:
            data['EMA_long'] = calculate_ema(data['Close'], self.ema_long_period)
        if 'ADX' not in data.columns:
            # Note: Proper ADX calculation requires more steps than simplified version.
            # Using simplified ADX for now, needs actual implementation for accuracy.
            data['ADX'] = calculate_adx(data['High'], data['Low'], data['Close'], self.adx_period)
        if 'ATR' not in data.columns:
            data['ATR'] = calculate_atr(data['High'], data['Low'], data['Close'], self.atr_period)
        if 'MACD_hist' not in data.columns:
            macd_line, signal_line, macd_hist = calculate_macd(data['Close'], self.ema_short_period, self.ema_long_period, 9) # Using EMA periods for MACD for consistency
            data['MACD'] = macd_line
            data['Signal'] = signal_line
            data['MACD_hist'] = macd_hist

        # Get the latest row of data
        latest_data = data.iloc[-1]
        
        # Ensure indicators are not NaN for the latest data point
        if latest_data.isnull().any():
            # If there are NaNs, especially in indicators, we might not be able to determine state.
            # This can happen at the beginning of the data series.
            return "Insufficient Data", 0.0

        # --- Market State Determination Logic ---
        state = "Neutral"
        score = 0.0
        
        # Trend Strength and Direction (using ADX and EMA)
        adx = latest_data['ADX']
        ema_short = latest_data['EMA_short']
        ema_long = latest_data['EMA_long']
        ema_diff = ema_short - ema_long
        ema_slope = data['EMA_short'].diff().iloc[-1] if len(data) > 1 else 0.0
        
        # Volatility (using ATR)
        atr = latest_data['ATR']
        # Calculate a relative volatility measure (e.g., ATR as % of Close price)
        relative_volatility = (atr / latest_data['Close']) * 100 if latest_data['Close'] != 0 else 0
        atr_high_threshold_pct = 2.0 # e.g., 2% of price is high volatility

        # MACD Histogram signal (simplified)
        macd_hist = latest_data['MACD_hist']

        # --- State Classification & Scoring ---
        
        # 1. Trend Strength
        trend_strength_score = 0.0
        if adx > self.adx_strong_trend_threshold:
            trend_strength_score = 1.0 # Strong trend detected
        elif adx > self.adx_moderate_trend_threshold:
            trend_strength_score = 0.6 # Moderate trend
        elif adx < self.adx_strong_trend_threshold and adx > self.adx_moderate_trend_threshold:
            trend_strength_score = 0.4 # Weak trend indication
        else: # adx < adx_moderate_trend_threshold
            trend_strength_score = 0.1 # Very weak trend / ranging indication

        # 2. Trend Direction
        direction_score = 0.0
        if ema_diff > 0 and ema_slope > 0: # EMA short > EMA long, and EMA short is rising
            direction_score = 1.0 # Clear uptrend direction
        elif ema_diff < 0 and ema_slope < 0: # EMA short < EMA long, and EMA short is falling
            direction_score = 1.0 # Clear downtrend direction
        elif abs(ema_diff) < (latest_data['Close'] * 0.005): # EMAs are very close (e.g., within 0.5% of price)
            direction_score = 0.2 # Low direction conviction / possibly ranging
        else:
            direction_score = 0.5 # Neutral or uncertain direction

        # 3. Volatility
        volatility_score = 0.0
        if relative_volatility > atr_high_threshold_pct:
            volatility_score = 1.0 # High volatility
        else:
            volatility_score = 0.3 # Lower volatility

        # 4. MACD Momentum (simplified)
        macd_momentum_score = 0.0
        if macd_hist > self.macd_hist_positive_threshold:
            macd_momentum_score = 0.6 # Positive momentum
        elif macd_hist < self.macd_hist_negative_threshold:
            macd_momentum_score = 0.6 # Negative momentum
        else:
            macd_momentum_score = 0.3 # Neutral momentum
            
        # --- Combine scores to determine state and confidence ---
        
        # Determine primary state based on strongest indicators
        if trend_strength_score >= 0.8 and direction_score >= 0.8:
            if state == "Neutral": # If not already set by stronger conditions
                if direction_score >= 0.8: # Clear trend direction
                    state = "Uptrend" if direction_score > 0.5 else "Downtrend"
                else:
                    state = "Uncertain Trend"
                score = (trend_strength_score * self.trend_strength_weight + 
                         direction_score * self.trend_direction_weight + 
                         volatility_score * self.volatility_weight +
                         macd_momentum_score * self.mac_weight) / (self.trend_strength_weight + self.trend_direction_weight + self.volatility_weight + self.mac_weight) # Normalize score
            
            if volatility_score == 1.0: # High volatility in a trend
                state = "Volatile " + state
            
        elif trend_strength_score < 0.5 and direction_score < 0.5:
            state = "Ranging"
            score = (trend_strength_score * 0.5 + # Less weight on weak trend strength
                     direction_score * 0.3 + 
                     volatility_score * 0.7) / (0.5 + 0.3 + 0.7) # Weight towards volatility for ranging
            if volatility_score == 1.0: # High volatility in ranging market
                state = "Choppy"
                score *= 0.9 # Slightly reduce score for choppiness
            
        else: # Mixed signals or uncertain conditions
            state = "Mixed/Uncertain"
            score = (trend_strength_score * 0.3 + 
                     direction_score * 0.3 + 
                     volatility_score * 0.4) / (0.3 + 0.3 + 0.4)

        # Final score adjustment and capping
        self.market_state = state
        self.confidence_score = max(0.1, min(1.0, score)) # Ensure score is between 0.1 and 1.0

        return self.market_state, self.confidence_score

# --- Example usage (would be called from ai_trader.py) ---
# This section is for standalone testing and demonstration.
# It will not be executed when this module is imported into ai_trader.py.
# if __name__ == "__main__":
#     # Dummy data for demonstration
#     # Ensure you have sufficient data points for indicators to calculate.
#     data_dict = {
#         'Open': [100, 102, 103, 105, 106, 107, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95],
#         'High': [103, 104, 106, 107, 108, 109, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96],
#         'Low': [99, 101, 102, 104, 105, 106, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95, 94],
#         'Close': [102, 103, 105, 106, 107, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95, 94],
#         'Volume': [1000, 1200, 1100, 1300, 1400, 1500, 1450, 1350, 1250, 1150, 1100, 1050, 1000, 950, 900, 850, 800, 750, 700, 650]
#     }
#     df = pd.DataFrame(data_dict)
#
#     # Ensure enough data points for indicators
#     # For ADX and ATR to be meaningful, we need at least `period` data points.
#     # For MACD, we need `slow_period + signal_period` data points.
#     # The dummy data above is already sufficient for the default periods.
#
#     analyzer = MarketStateAnalyzer()
#     state, score = analyzer.analyze(df)
#     print(f"Current Market State: {state}, Confidence Score: {score:.2f}")

