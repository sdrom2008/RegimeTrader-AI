"""
查看 v2_quantile 模型的特征重要性
"""

import pandas as pd
import pickle

# 加载模型
with open('regime_model_v2_quantile.pkl', 'rb') as f:
    model = pickle.load(f)

print("Model classes:", model.classes_)
print("N_estimators:", model.n_estimators)
print("\nTop 15 Feature Importances:")

# 特征列表（与训练时一致）
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
    'Price_std_20',
    'ATR_ratio',
    'Drawdown_20',
    'RSI_dev'
]

importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
for i, (feat, imp) in enumerate(importances.head(15).items(), 1):
    print(f"{i:2}. {feat:<25} {imp:.4f}")

print("\nTotal features:", len(feature_cols))
print("Model size: ~35 MB")
print("Class mapping: {0:'Down', 1:'Osc', 2:'Up'}")
