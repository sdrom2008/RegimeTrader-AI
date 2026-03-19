"""
快速验证 v2 模型在 BTC 上的信号
"""

import os, sys, datetime, ccxt, pandas as pd
import pickle
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2 as calculate_features
from regime_trader_ai_product.config_v2 import (
    ADX_STRONG_THRESHOLD, ADX_WEAK_THRESHOLD,
    CONFIDENCE_THRESHOLD, LEVERAGE, RISK_PER_TRADE_PCT,
    STOP_LOSS_ATR_MULT, TAKE_PROFIT_RR
)

MODEL_FILE = 'regime_model_v2.pkl'

def main():
    # 加载模型
    with open(MODEL_FILE, 'rb') as f:
        model = pickle.load(f)
    print("[+] Model loaded")

    # 获取 BTC 1h 数据
    exchange = ccxt.binance({'enableRateLimit': True})
    print("[*] Fetching BTC/USDT 1h data...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=250)
    df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # 计算特征
    df_feat = calculate_features(df.copy())
    latest = df_feat.iloc[-1]

    # 提取特征（必须与训练时完全一致）
    from regime_trader_ai_product.strategy_v2_constants import get_feature_columns
    feature_cols = get_feature_columns()
    X = latest[feature_cols].values.reshape(1, -1)

    # 预测
    pred = model.predict(X)[0]
    probs = model.predict_proba(X)[0]
    conf = probs[pred]

    print(f"\n=== BTC/USDT 最新信号 ===")
    print(f"时间: {df.index[-1]}")
    print(f"价格: ${latest['Close']:.2f}")
    print(f"ADX: {latest['ADX']:.1f} | +DI: {latest['+DI']:.1f} | -DI: {latest['-DI']:.1f}")
    print(f"MACD hist: {latest['MACD_hist']:.4f}")
    print(f"价格/EMA200: {latest['Price_vs_EMA200']*100:+.1f}%")
    print(f"模型预测: {pred} ({['DOWN','OSC','UP'][pred]})")
    print(f"置信度: {conf:.2%}")

    # 信号判断
    adx = latest['ADX']
    print(f"[DEBUG] ADX={adx:.1f} (>= {ADX_STRONG_THRESHOLD}?)")
    print(f"[DEBUG] confidence={conf:.2%} (>= {CONFIDENCE_THRESHOLD}?)")
    print(f"[DEBUG] pred={pred} (0=Down,1=Osc,2=Up)")
    if adx >= ADX_STRONG_THRESHOLD and conf >= CONFIDENCE_THRESHOLD:
        if pred == 2:
            signal = "BUY"
            reason = f"强趋势上涨 (ADX>{ADX_STRONG_THRESHOLD}, 置信度{conf:.1%})"
        elif pred == 0:
            signal = "SELL"
            reason = f"强趋势下跌 (ADX>{ADX_STRONG_THRESHOLD}, 置信度{conf:.1%})"
        else:
            signal = "HOLD"
            reason = "模型预测震荡"
    elif adx <= ADX_WEAK_THRESHOLD:
        signal = "HOLD"
        reason = f"ADX={adx:.1f} <{ADX_WEAK_THRESHOLD} (震荡过滤)"
    else:
        signal = "HOLD"
        reason = f"置信度不足或中性趋势"

    print(f"\n交易信号: {signal}")
    print(f"理由: {reason}")

    if signal in ["BUY","SELL"]:
        atr = latest['ATR']
        price = latest['Close']
        if signal == "BUY":
            sl = price - atr * STOP_LOSS_ATR_MULT
            tp = price + (price - sl) * TAKE_PROFIT_RR
        else:
            sl = price + atr * STOP_LOSS_ATR_MULT
            tp = price - (sl - price) * TAKE_PROFIT_RR
        print(f"止损价: ${sl:.4f}")
        print(f"止盈价: ${tp:.4f}")

if __name__ == '__main__':
    main()
