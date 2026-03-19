"""批量扫描前20币种的信号（用于调试阈值）"""
import os, sys, ccxt, pandas as pd, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2
from regime_trader_ai_product.config_v2 import ADX_STRONG_THRESHOLD, CONFIDENCE_THRESHOLD

model = pickle.load(open('regime_model_v2_quantile.pkl','rb'))
features = ['ADX','+DI','-DI','DI_diff','MACD_hist','MACD_hist_cross_up','RSI','ATR','Price_vs_EMA200','Volume_Change_Ratio','EMA_50','EMA_200','ADX_strong','ADX_weak','+DI_cross_above_-DI','-DI_cross_above_+DI','MACD_hist_positive','Price_std_20','ATR_ratio','Drawdown_20','RSI_dev']
ex = ccxt.binance({'enableRateLimit':True})
tickers = ex.fetch_tickers()
syms = [s for s,t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
syms.sort(key=lambda s: (tickers[s].get('quoteVolume') or 0), reverse=True)
syms = syms[:20]
print(f"{'Symbol':<12} {'ADX':<5} {'+DI':<5} {'-DI':<5} {'Pred':<4} {'Conf':<5} {'Signal'}")
count_sig = 0
for s in syms:
    try:
        ohlcv = ex.fetch_ohlcv(s,'1h',limit=250)
        df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        if len(df)<200: continue
        df_feat = prepare_features_v2(df)
        if df_feat.empty: continue
        latest = df_feat.iloc[-1]
        X = latest[features].values.reshape(1,-1)
        pred = model.predict(X)[0]
        conf = model.predict_proba(X)[0][pred]
        adx, plus_di, minus_di = latest['ADX'], latest['+DI'], latest['-DI']
        signal = None
        if adx>=ADX_STRONG_THRESHOLD and conf>=CONFIDENCE_THRESHOLD:
            if pred==2: signal='BUY'
            elif pred==0: signal='SELL'
        if signal: count_sig += 1
        print(f"{s:<12} {adx:5.1f} {plus_di:5.1f} {minus_di:5.1f} {pred:>3}   {conf:5.1%}   {signal}")
    except: pass
print(f"\nSignals found (ADX>={ADX_STRONG_THRESHOLD}, conf>={CONFIDENCE_THRESHOLD}): {count_sig}")
