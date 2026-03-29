"""
训练三分类模型 - 使用分位数标签（适应波动）
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2, label_data_3class_quantile

# 数据文件（优先6年，否则用2年）
DATA_FILE_6Y = 'data/BTC_USDT_1h_6y.csv'
DATA_FILE_2Y = 'data/BTC_USDT_1h_2y_features.csv'

if os.path.exists(DATA_FILE_6Y):
    data_file = DATA_FILE_6Y
    print("[*] Using 6-year data")
else:
    data_file = DATA_FILE_2Y
    print("[*] Using 2-year data (6-year not found)")

def train():
    print(f"[*] Loading data from {data_file}...")
    df = pd.read_csv(data_file, index_col='timestamp', parse_dates=True)
    print(f"[+] Loaded {len(df)} rows")

    # 特征工程
    print("[*] Calculating features...")
    df = prepare_features_v2(df)

    # 标签（分位数阈值）
    print("[*] Generating labels (quantile-based)...")
    df = label_data_3class_quantile(df)

    # 特征列（包含新增统计特征）
    feature_cols = [
        'ADX', '+DI', '-DI', 'DI_diff',
        'MACD_hist', 'MACD_hist_cross_up',
        'RSI', 'ATR',
        'Price_vs_EMA200',
        'Volume_Change_Ratio',
        'EMA_50', 'EMA_200',
        'ADX_strong', 'ADX_weak',
        '+DI_cross_above_-DI', '-DI_cross_above_+DI',
        'MACD_hist_positive',
        # 新增统计特征
        'Price_std_20',
        'ATR_ratio',
        'Drawdown_20',
        'RSI_dev'
    ]

    X = df[feature_cols]
    y = df['regime']

    print(f"\n[*] Dataset: {len(X)} samples, {len(feature_cols)} features")
    print("[*] Label distribution:")
    print(y.value_counts().sort_index())
    print(y.value_counts(normalize=True).sort_index())

    # 划分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[*] Train: {len(X_train)}, Test: {len(X_test)}")

    # 模型
    print("[*] Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=18,
        min_samples_split=15,
        min_samples_leaf=8,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    model.fit(X_train, y_train)

    # 评估
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Down (0)', 'Osc (1)', 'Up (2)']))

    # 特征重要性
    imp = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\nTop 15 Features:")
    print(imp.head(15))

    # 保存
    model_file = 'regime_model_v2_quantile.pkl'
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n[+] Model saved to {model_file}")

if __name__ == '__main__':
    train()
