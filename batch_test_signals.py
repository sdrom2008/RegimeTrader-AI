"""
批量测试 v2_quantile 模型在多个币种上的信号
"""

import os, sys, datetime, ccxt, pandas as pd, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2

MODEL_FILE = 'regime_model_v2_quantile.pkl'
model = pickle.load(open(MODEL_FILE, 'rb'))

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
    'Price_std_20', 'ATR_ratio', 'Drawdown_20', 'RSI_dev'
]

exchange = ccxt.binance({'enableRateLimit':True})
tickers = exchange.fetch_tickers()
symbols = [s for s,t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
symbols.sort(key=lambda s: tickers[s].get('quoteVolume',0), reverse=True)
symbols = symbols[:15]  # 测试15个

print(f"{'Time':<20} {'Symbol':<12} {'Price':<12} {'Signal':<6} {'Conf':<6} {'ADX':<6} {'+DI':<6} {'-DI':<6}")
print("-"*90)

for symbol in symbols:
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
        df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        if len(df) < 200: continue
        df_feat = prepare_features_v2(df.copy())
        if df_feat.empty: continue
        latest = df_feat.iloc[-1]
        X = latest[feature_cols].values.reshape(1,-1)
        pred = model.predict(X)[0]
        conf = model.predict_proba(X)[0][pred]
        adx, plus_di, minus_di = latest['ADX'], latest['+DI'], latest['-DI']
        print(f"{df.index[-1].strftime('%H:%M'):<20} {symbol:<12} ${latest['Close']:<11.4f} {pred:<6} {conf:<6.2%} {adx:<6.1f} {plus_di:<6.1f} {minus_di:<6.1f}")
    except Exception as e:
        continue
