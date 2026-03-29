"""
三分类标签生成 + 特征工程
使用 BTC 2年数据训练三分类模型
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
from regime_trader_ai_product.strategy_v2 import calculate_features, label_data_3class

DATA_FILE = 'data/BTC_USDT_1h_2y_features.csv'
MODEL_OUTPUT = 'regime_model_v2.pkl'

def load_and_prepare():
    df = pd.read_csv(DATA_FILE, index_col='timestamp', parse_dates=True)
    print(f"[*] Loaded {len(df)} rows from {DATA_FILE}")

    # 确保基础指标存在
    if 'ADX_14' in df.columns and 'ATRr_14' in df.columns:
        # 重命名列以匹配策略_v2 函数预期
        df = df.rename(columns={
            'ADX_14': 'ADX',
            'ATRr_14': 'ATR',
            'BBL_20_2.0_2.0': 'BBL',
            'BBM_20_2.0_2.0': 'BBM',
            'BBU_20_2.0_2.0': 'BBU',
            'RSI_14': 'RSI',
            'EMA_50': 'EMA_50',
            'EMA_200': 'EMA_200',
        })

    # 重新计算所有特征（使用策略_v2的统一函数）
    df = calculate_features(df)

    # 三分类标签
    df = label_data_3class(df)

    return df

def train():
    df = load_and_prepare()

    # 特征列表（与strategy_v2一致）
    features = [
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

    # 确保所有特征存在
    missing = [f for f in features if f not in df.columns]
    if missing:
        print(f"[!] Missing features: {missing}")
        return

    X = df[features]
    y = df['regime']

    print(f"\n[*] Dataset size: {len(X)}")
    print(f"[*] Feature count: {len(features)}")
    print(f"[*] Label distribution:")
    print(y.value_counts().sort_index())
    print(f"[*] Label proportions:")
    print(y.value_counts(normalize=True).sort_index())

    # 划分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\n[*] Training set: {len(X_train)}, Test set: {len(X_test)}")

    # 模型
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

    print("[*] Fitting model...")
    model.fit(X_train, y_train)

    # 评估
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n=== Evaluation ===")
    print(f"Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Down (0)', 'Osc (1)', 'Up (2)']))

    # 特征重要性
    imp = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
    print("\nTop 15 Features:")
    print(imp.head(15))

    # 保存
    with open(MODEL_OUTPUT, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n[+] Model saved to {MODEL_OUTPUT}")

if __name__ == '__main__':
    train()
