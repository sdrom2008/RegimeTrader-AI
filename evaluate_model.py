import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import pickle

# Load data
df = pd.read_csv('data/BTC_USDT_1h_2y_features.csv', index_col='timestamp', parse_dates=True)

# Label data
look_forward_candles = 24
atr_multiplier = 3
future_high = df['High'].shift(-look_forward_candles).rolling(window=look_forward_candles).max()
future_low = df['Low'].shift(-look_forward_candles).rolling(window=look_forward_candles).min()
future_price_range = future_high - future_low
trend_threshold = df['ATRr_14'] * atr_multiplier
df['regime'] = np.where(future_price_range > trend_threshold, 1, 0)
df.dropna(subset=['regime'], inplace=True)

# Features
features = [col for col in df.columns if 'ADX' in col or 'DMP' in col or 'DMN' in col or 'BB' in col or 'ATR' in col or 'RSI' in col or 'EMA' in col or 'DIST' in col]
X = df[features]
y = df['regime']

print(f"Total samples: {len(df)}")
print(f"Class distribution:\n{y.value_counts()}")
print(f"Class proportion:\n{y.value_counts(normalize=True)}")

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Load trained model
with open('regime_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Evaluate
y_pred = model.predict(X_test)
print("\n=== Model Evaluation on Test Set ===")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Range (0)', 'Trend (1)']))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Show feature importance
importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
print("\nTop 10 Feature Importances:")
print(importances.head(10))
