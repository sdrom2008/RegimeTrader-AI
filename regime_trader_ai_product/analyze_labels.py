import pandas as pd
import numpy as np

# Load features data
df = pd.read_csv('data/BTC_USDT_1h_2y_features.csv', index_col='timestamp', parse_dates=True)

# Calculate labels using same parameters as training
look_forward_candles = 24
atr_multiplier = 3

future_high = df['High'].shift(-look_forward_candles).rolling(window=look_forward_candles).max()
future_low = df['Low'].shift(-look_forward_candles).rolling(window=look_forward_candles).min()
future_price_range = future_high - future_low
trend_threshold = df['ATRr_14'] * atr_multiplier
df['regime'] = np.where(future_price_range > trend_threshold, 1, 0)
df.dropna(subset=['regime'], inplace=True)

# Distribution
print("标签分布:")
print(df['regime'].value_counts())
print("\n比例:")
print(df['regime'].value_counts(normalize=True))

# Show some example rows where regime=1 (trend) and regime=0 (range)
print("\n=== Trend (1) samples (head):")
print(df[df['regime']==1][['Close','ADX_14','ATRr_14','BB_WIDTH','regime']].head(10))

print("\n=== Range (0) samples (head):")
print(df[df['regime']==0][['Close','ADX_14','ATRr_14','BB_WIDTH','regime']].head(10))
