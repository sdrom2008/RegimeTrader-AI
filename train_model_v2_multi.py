"""
Multi-symbol three-class regime model trainer.

Loads BTC/ETH/BNB/SOL/XRP 6y 1h CSVs, builds quantile labels + v2 features,
concatenates, trains RandomForest (same settings as quantile trainer), and
saves regime_model_v2_multi_full.pkl + meta JSON.
"""

from __future__ import annotations

import json
import os
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from strategy_v2_quantile import label_data_3class_quantile, prepare_features_v2

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(REPO_ROOT, "data")
SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
MODEL_FILE = os.path.join(REPO_ROOT, "regime_model_v2_multi_full.pkl")
META_FILE = os.path.join(REPO_ROOT, "regime_model_v2_multi_full_meta.json")

FEATURE_COLS = [
    "ADX", "+DI", "-DI", "DI_diff",
    "MACD_hist", "MACD_hist_cross_up",
    "RSI", "ATR",
    "Price_vs_EMA200",
    "Volume_Change_Ratio",
    "EMA_50", "EMA_200",
    "ADX_strong", "ADX_weak",
    "+DI_cross_above_-DI", "-DI_cross_above_+DI",
    "MACD_hist_positive",
    "Price_std_20",
    "ATR_ratio",
    "Drawdown_20",
    "RSI_dev",
]

LOOK_FORWARD = 24
QUANTILE_THRESHOLD = 0.6


def load_symbol(symbol: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{symbol}_USDT_1h_6y.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")
    df = pd.read_csv(path, index_col="timestamp", parse_dates=True)
    print(f"[+] {symbol}: loaded {len(df)} rows from {path}")
    df = prepare_features_v2(df)
    df = label_data_3class_quantile(
        df, look_forward_candles=LOOK_FORWARD, quantile_threshold=QUANTILE_THRESHOLD
    )
    missing = [c for c in FEATURE_COLS + ["regime"] if c not in df.columns]
    if missing:
        raise RuntimeError(f"{symbol}: missing columns after feature/label: {missing}")
    df = df[FEATURE_COLS + ["regime"]].copy()
    df["symbol"] = symbol
    print(f"    usable samples after features/labels: {len(df)}")
    return df


def train():
    frames = []
    for sym in SYMBOLS:
        frames.append(load_symbol(sym))
    df = pd.concat(frames, axis=0, ignore_index=True)
    print(f"\n[*] Combined dataset: {len(df)} samples across {len(SYMBOLS)} symbols")

    X = df[FEATURE_COLS]
    y = df["regime"].astype(int)

    print("[*] Label distribution:")
    print(y.value_counts().sort_index())
    print(y.value_counts(normalize=True).sort_index())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[*] Train: {len(X_train)}, Test: {len(X_test)}")

    print("[*] Training RandomForest (multi-symbol)...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=18,
        min_samples_split=15,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, target_names=["Down (0)", "Osc (1)", "Up (2)"]
    )
    report_dict = classification_report(
        y_test, y_pred, target_names=["Down (0)", "Osc (1)", "Up (2)"], output_dict=True
    )
    print(f"\nAccuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(report)

    imp = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(
        ascending=False
    )
    print("\nTop 15 Features:")
    print(imp.head(15))

    # Replace symlink with a real file if present
    if os.path.islink(MODEL_FILE) or os.path.exists(MODEL_FILE):
        os.remove(MODEL_FILE)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model, f)
    print(f"\n[+] Model saved to {MODEL_FILE}")

    class_counts = y.value_counts().sort_index()
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "symbols": SYMBOLS,
        "num_samples": int(len(df)),
        "class_distribution": [int(class_counts.get(i, 0)) for i in (0, 1, 2)],
        "accuracy": float(acc),
        "classification_report": report_dict,
        "feature_importance": [
            {"feature": k, "importance": float(v)} for k, v in imp.items()
        ],
        "feature_list": FEATURE_COLS,
        "config": {
            "n_estimators": 300,
            "max_depth": 18,
            "min_samples_split": 15,
            "min_samples_leaf": 8,
            "class_weight": "balanced",
            "look_forward_candles": LOOK_FORWARD,
            "quantile_threshold": QUANTILE_THRESHOLD,
        },
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] Meta saved to {META_FILE}")
    return acc, report, MODEL_FILE


if __name__ == "__main__":
    train()
