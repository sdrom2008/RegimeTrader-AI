"""
搜索最优的 ADX 和置信度阈值组合
目标：最大化 Up/Down 类别的召回率（避免漏信号）
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pickle
import numpy as np
from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2, label_data_3class_quantile
from regime_trader_ai_product.config_v2 import ADX_STRONG_THRESHOLD as ADX_DEFAULT

DATA_FILE = 'data/BTC_USDT_1h_6y.csv'
MODEL_FILE = 'regime_model_v2_quantile.pkl'

# 加载模型
with open(MODEL_FILE, 'rb') as f:
    model = pickle.load(f)

# 加载并特征化数据
df = pd.read_csv(DATA_FILE, index_col='timestamp', parse_dates=True)
df = prepare_features_v2(df)
df = label_data_3class_quantile(df)  # 使用同标签方法

# 划分测试集（最后20%）
split_idx = int(len(df) * 0.8)
df_test = df.iloc[split_idx:].copy()

# 特征列表
features = [
    'ADX', '+DI', '-DI', 'DI_diff',
    'MACD_hist', 'MACD_hist_cross_up',
    'RSI', 'ATR',
    'Price_vs_EMA200',
    'Volume_Change_Ratio',
    'EMA_50', 'EMA_200',
    'ADX_strong', 'ADX_weak',
    '+DI_cross_above_-DI', '-DI_cross_above_+DI',
    'MACD_hist_positive',
    'Price_std_20', 'ATR_ratio', 'Drawdown_20', 'RSI_dev'
]

X_test = df_test[features]
y_test = df_test['regime']

# 预测
preds = model.predict(X_test)
probs = model.predict_proba(X_test)

print(f"Test set size: {len(X_test)}")
print(f"Label distribution:\n{pd.Series(y_test).value_counts().sort_index()}\n")

# 阈值搜索
adx_values = [20, 22, 25]
conf_values = [0.45, 0.50, 0.55, 0.60]

results = []

for adx_thresh in adx_values:
    for conf_thresh in conf_values:
        # 模拟信号生成（只考虑 Up/Down）
        signals = []
        for i, (pred, prob, adx) in enumerate(zip(preds, probs, df_test['ADX'].values)):
            confidence = prob[pred]
            if adx >= adx_thresh and confidence >= conf_thresh:
                if pred in [0, 2]:
                    signals.append(pred)
                else:
                    signals.append(None)
            else:
                signals.append(None)

        # 统计：使用 numpy 数组避免索引问题
        signals_arr = np.array(signals)
        mask = ~pd.isna(signals_arr)
        signal_count = mask.sum()

        if signal_count == 0:
            recall_up = recall_down = 0.0
            accuracy = np.nan
        else:
            # 在产生信号的样本中，有多少是真实 Up/Down
            true_labels = y_test.values[mask]
            pred_labels = signals_arr[mask]
            correct = (true_labels == pred_labels)
            accuracy = correct.mean()

            # 分别计算 Up/Down 的召回率
            up_mask_test = (y_test.values == 2)
            down_mask_test = (y_test.values == 0)

            up_signals = (signals_arr == 2) & up_mask_test
            down_signals = (signals_arr == 0) & down_mask_test

            recall_up = up_signals.sum() / up_mask_test.sum() if up_mask_test.sum() > 0 else 0
            recall_down = down_signals.sum() / down_mask_test.sum() if down_mask_test.sum() > 0 else 0

        results.append({
            'adx_thresh': adx_thresh,
            'conf_thresh': conf_thresh,
            'total_signals': signal_count,
            'signal_accuracy': accuracy if signal_count>0 else np.nan,
            'recall_up': recall_up,
            'recall_down': recall_down,
            'recall_avg': (recall_up + recall_down) / 2
        })

# 输出表格
print("\n=== Threshold Grid Search Results ===")
print(f"{'ADX':<4} {'Conf':<5} {'Signals':<8} {'Acc':<5} {'Rec Up':<6} {'Rec Down':<8} {'Avg Rec':<7}")
for r in results:
    print(f"{r['adx_thresh']:<4} {r['conf_thresh']:<5.2f} {r['total_signals']:<8} "
          f"{r.get('signal_accuracy', 0):<5.2f} {r['recall_up']:<6.2%} {r['recall_down']:<8.2%} {r['recall_avg']:<7.2%}")
