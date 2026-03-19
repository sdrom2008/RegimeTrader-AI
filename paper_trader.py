"""
v2 策略执行器 - 干跑/实盘统一入口
支持：三分类模型 + 双向交易 + 动态风控
"""

import os
import sys
import json
import datetime
import time
import logging
import pandas as pd
import ccxt
import pickle
import subprocess
import shutil
import requests
import feedparser
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_trader_ai_product.logger_v2 import setup_logger
from regime_trader_ai_product.strategy_v2_quantile import prepare_features_v2
from regime_trader_ai_product.config import (
    ADX_STRONG_THRESHOLD, ADX_WEAK_THRESHOLD,
    CONFIDENCE_THRESHOLD, LEVERAGE, RISK_PER_TRADE_PCT,
    STOP_LOSS_ATR_MULT, TAKE_PROFIT_RR, TRAILING_STOP_ATR,
    SCAN_LIMIT, STATE_FILE, MODEL_FILE, ENABLE_FUNDING_FILTER,
    FUNDING_RATE_THRESHOLD
)
from regime_trader_ai_product.news_fetcher import fetch_all_news
from regime_trader_ai_product.sentiment_analyzer import SentimentAnalyzer
from regime_trader_ai_product.risk_controller import RiskController

# 初始化日志
logger = setup_logger()

DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'

# 宏风险监控（全局单例，避免重复抓取）
RISK_CHECK_INTERVAL = 600  # 秒，10分钟
_last_risk_check = None
_risk_assessment_cache = None

def get_macro_risk_assessment(force=False):
    """获取宏观风险评级（带缓存，10分钟更新一次）"""
    global _last_risk_check, _risk_assessment_cache
    
    now = time.time()
    if force or (_last_risk_check is None) or (now - _last_risk_check >= RISK_CHECK_INTERVAL):
        logger.debug("Fetching macro news and analyzing risk...")
        try:
            news = fetch_all_news(max_per_source=5)
            analyzer = SentimentAnalyzer()
            risk_score, has_critical, details = analyzer.analyze_news_list(news)
            controller = RiskController()
            assessment = controller.assess_risk(risk_score, has_critical, details)
            _risk_assessment_cache = assessment
            _last_risk_check = now
            
            # 发送警报（如果需要）
            if assessment['level'] >= 1 and SEND_WHATSAPP_ALERT:
                alert_msg = controller.format_alert(assessment)
                send_whatsapp_alert(alert_msg)
            
            logger.info(f"Macro risk assessment: level={assessment['level']} score={risk_score:.1%}")
        except Exception as e:
            logger.error(f"Macro risk check failed: {e}")
            # 出错时返回上次缓存或默认为正常
            if _risk_assessment_cache:
                return _risk_assessment_cache
            return {'level': 0, 'action': 'NORMAL', 'risk_score': 0.0, 'details': []}
    
    return _risk_assessment_cache

def send_whatsapp_alert(message):
    """发送 WhatsApp 通知（生产模式）"""
    logger.info(f"[WhatsApp] {message}")
    if DRY_RUN:
        logger.debug("WhatsApp dry-run: skip sending")
        return
    safe_msg = message.replace("'", "'\\''")
    target = "+8613908412393"
    openclaw_path = "/home/sdrom2008/.npm-global/bin/openclaw"
    if not os.path.exists(openclaw_path):
        openclaw_path = shutil.which("openclaw") or "openclaw"
    cmd = f"{openclaw_path} message send --channel whatsapp --target '{target}' --message '{safe_msg}'"
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info("WhatsApp sent")
    except Exception as e:
        logger.error(f"WhatsApp failed: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'balance': 10000.0, 'positions': {}, 'trade_history': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def scan_and_trade_v2():
    logger.info(f"{'='*60}")
    logger.info(f"🚀 RegimeTrader AI v2 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    # 加载模型
    try:
        with open(MODEL_FILE, 'rb') as f:
            model = pickle.load(f)
        logger.info("Model loaded")
    except Exception as e:
        logger.error(f"Model not found: {e}. Please run: python train_model_v2_quantile.py")
        return

    # 加载状态
    state = load_state()
    balance = state['balance']
    positions = state['positions']
    logger.info(f"Balance: ${balance:.2f} | Positions: {len(positions)}")

    fee_rate = 0.0004
    exchange = ccxt.binance({'enableRateLimit': True})

    # 1) 更新持仓
    closed_positions = []
    unrealized_total = 0.0

    for sym, pos in list(positions.items()):
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry = pos['entry_price']
            amount = pos['amount']
            atr = pos['atr']
            sl = pos['sl']

            if pos['type'] == 'BUY':
                unreal = (price - entry) * amount
                unrealized_total += unreal
                if price > pos.get('highest_seen', entry):
                    pos['highest_seen'] = price
                    pos['sl'] = max(sl, price - atr * TRAILING_STOP_ATR)
                if price <= sl:
                    exit_price = sl
                    pnl = (exit_price - entry) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    logger.info(f"CLOSED LONG {sym} @{exit_price:.4f} PnL:${pnl:.2f}")
            elif pos['type'] == 'SELL':
                unreal = (entry - price) * amount
                unrealized_total += unreal
                if price < pos.get('lowest_seen', entry):
                    pos['lowest_seen'] = price
                    pos['sl'] = min(sl, price + atr * TRAILING_STOP_ATR)
                if price >= sl:
                    exit_price = sl
                    pnl = (entry - exit_price) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee))
                    logger.info(f"CLOSED SHORT {sym} @{exit_price:.4f} PnL:${pnl:.2f}")
        except Exception as e:
            logger.warning(f"{sym} update error: {e}")

    # 记录平仓历史
    for sym, pnl, fee in closed_positions:
        positions.pop(sym, None)
        state['trade_history'].append({
            'symbol': sym,
            'pnl': pnl,
            'fee': fee,
            'exit_time': datetime.datetime.utcnow().isoformat()+'Z'
        })

    # 2) 计算总权益
    margin_used = sum(p['margin'] for p in positions.values())
    total_equity = balance + margin_used + unrealized_total
    logger.info(f"Equity: ${total_equity:.2f} | Cash: ${balance:.2f} | Margin: ${margin_used:.2f}")

    # 3) 宏观风险检查（每10分钟更新一次）
    macro_risk = get_macro_risk_assessment()
    if macro_risk['level'] == 2:
        logger.warning(f"🛡️ Macro risk CRITICAL: {macro_risk['reason']} - Skipping new entries")
        # 仍保存状态，但不新开仓
        state['balance'] = balance
        state['positions'] = positions
        save_state(state)
        # 输出摘要并退出扫描
        logger.info(f"\n--- Summary (Risk Halt) ---")
        logger.info(f"Equity: ${total_equity:.2f} ({((total_equity/10000)-1)*100:+.1f}%)")
        logger.info(f"Closed positions: {len(closed_positions)}")
        logger.info(f"New entries: 0 (MACRO RISK CRITICAL)")
        return
    elif macro_risk['level'] == 1:
        logger.info(f"🛡️ Macro risk WARNING: {macro_risk['reason']} - Reducing position size")
        # 在后续仓位计算中使用 reduced_risk_pct
        adjusted_risk_pct = RISK_PER_TRADE_PCT * 0.5
    else:
        adjusted_risk_pct = RISK_PER_TRADE_PCT

    # 4) 扫描新机会
    logger.info(f"Scanning top {SCAN_LIMIT} symbols...")
    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers()
        usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
        usdt_pairs.sort(key=lambda s: (tickers[s].get('quoteVolume') or 0), reverse=True)
        symbols = usdt_pairs[:SCAN_LIMIT]
    except Exception as e:
        logger.error(f"Fetch tickers failed: {e}")
        symbols = []

    new_entries = []

    for symbol in symbols:
        if symbol in positions:
            continue
        time.sleep(0.2)

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            if len(df) < 200:
                continue

            df_feat = prepare_features_v2(df.copy())
            if df_feat.empty:
                continue

            latest = df_feat.iloc[-1]
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
            X = latest[features].values.reshape(1, -1)

            pred = model.predict(X)[0]
            probs = model.predict_proba(X)[0]
            confidence = probs[pred]
            adx = latest['ADX']

            # 信号判断
            signal = None
            if adx >= ADX_STRONG_THRESHOLD and confidence >= CONFIDENCE_THRESHOLD:
                if pred == 2:
                    signal = "BUY"
                elif pred == 0:
                    signal = "SELL"

            if signal:
                entry_price = latest['Close']
                atr = latest['ATR']

                # 止损止盈
                if signal == "BUY":
                    sl_price = entry_price - atr * STOP_LOSS_ATR_MULT
                    tp_price = entry_price + (entry_price - sl_price) * TAKE_PROFIT_RR
                else:
                    sl_price = entry_price + atr * STOP_LOSS_ATR_MULT
                    tp_price = entry_price - (sl_price - entry_price) * TAKE_PROFIT_RR

                # 仓位计算
                price_risk = abs(entry_price - sl_price)
                if price_risk <= 0:
                    continue
                risk_amount = total_equity * adjusted_risk_pct
                amount = risk_amount / price_risk
                max_notional = total_equity * LEVERAGE
                if amount * entry_price > max_notional:
                    amount = max_notional / entry_price
                margin_req = (amount * entry_price) / LEVERAGE

                used_margin = sum(p['margin'] for p in positions.values())
                if margin_req > (total_equity - used_margin):
                    continue

                # 开仓
                balance -= margin_req
                pos = {
                    'type': signal,
                    'entry_price': entry_price,
                    'amount': amount,
                    'margin': margin_req,
                    'atr': atr,
                    'sl': sl_price,
                    'tp': tp_price,
                    'highest_seen': entry_price if signal == "BUY" else None,
                    'lowest_seen': entry_price if signal == "SELL" else None,
                    'entry_time': datetime.datetime.utcnow().isoformat()+'Z',
                    'confidence': confidence
                }
                positions[symbol] = pos
                new_entries.append(f"{symbol} {signal} @{entry_price:.4f} SL:{sl_price:.4f}")
                logger.info(f"NEW {signal} {symbol} @{entry_price:.4f} | ATR:{atr:.4f} Amount:{amount:.4f}")

        except Exception as e:
            logger.warning(f"{symbol} scan error: {e}")

    # 4) 保存状态
    state['balance'] = balance
    state['positions'] = positions
    save_state(state)

    # 5) 输出摘要
    logger.info(f"\n--- Summary ---")
    logger.info(f"Equity: ${total_equity:.2f} ({((total_equity/10000)-1)*100:+.1f}%)")
    logger.info(f"Closed positions: {len(closed_positions)}")
    for sym, pnl, fee in closed_positions:
        logger.info(f"  {sym}: ${pnl:+.2f}")
    logger.info(f"New entries: {len(new_entries)}")
    for e in new_entries:
        logger.info(f"  {e}")

if __name__ == '__main__':
    scan_and_trade_v2()
