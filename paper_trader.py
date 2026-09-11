"""
v2 策略执行器 - 干跑/实盘统一入口
支持：三分类模型 + 双向交易 + 动态风控
信号观察模式：记 journal、不新开仓；已有仓位仍正常平仓
"""

import os
import sys
import json
import datetime
import time
import logging
import warnings
import pandas as pd
import ccxt
import pickle
import subprocess
import shutil
import requests
import feedparser
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_v2 import setup_logger
from strategy_v2_quantile import prepare_features_v2
from config import (
    ADX_STRONG_THRESHOLD, ADX_WEAK_THRESHOLD, MIN_DI_DIFF,
    CONFIDENCE_THRESHOLD, LEVERAGE, RISK_PER_TRADE_PCT,
    STOP_LOSS_ATR_MULT, TAKE_PROFIT_RR, TRAILING_STOP_ATR,
    SCAN_LIMIT, STATE_FILE, MODEL_FILE, ENABLE_FUNDING_FILTER,
    FUNDING_RATE_THRESHOLD, TRADING_SYMBOLS, resolve_model_file,
    COOLDOWN_HOURS, MIN_BARS_BETWEEN_TRADES, MAX_CONCURRENT_POSITIONS,
    MAX_HOLD_HOURS,
    SIGNAL_OBSERVE_MODE, SIGNAL_JOURNAL_FILE,
    ENTRY_ON_CLOSED_1H_ONLY,
    SLIPPAGE_BPS, SLIPPAGE_ATR_FRAC,
    TRAIL_ACTIVATE_R, MAX_MARGIN_PCT_OF_EQUITY,
)

# from news_fetcher import fetch_all_news
# from sentiment_analyzer import SentimentAnalyzer
# from risk_controller import RiskController

# 初始化日志
logger = setup_logger()

# Quiet sklearn "X does not have valid feature names" on every predict
warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names",
    category=UserWarning,
)

DRY_RUN = os.environ.get('DRY_RUN', '0') == '1'

CLASS_NAMES = {0: 'Down', 1: 'Osc/HOLD', 2: 'Up'}

# 宏风险监控（全局单例，避免重复抓取）
RISK_CHECK_INTERVAL = 600  # 秒，10分钟
_last_risk_check = None
_risk_assessment_cache = None

def get_macro_risk_assessment(force=False):
    """获取宏观风险评级（临时禁用，返回正常）"""
    return {'level': 0, 'action': 'NORMAL', 'risk_score': 0.0, 'details': []}

def send_whatsapp_alert(message):
    """发送 WhatsApp 通知（生产模式）"""
    logger.info(f"[WhatsApp] {message}")
    if DRY_RUN:
        logger.debug("WhatsApp dry-run: skip sending")
        return
    safe_msg = message.replace("'", "'\\''")
    target = "+8613908412393"
    openclaw_path = shutil.which("openclaw") or os.path.expanduser("~/.npm-global/bin/openclaw")
    if not os.path.exists(openclaw_path):
        openclaw_path = "openclaw"
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
    return {'balance': 10000.0, 'positions': {}, 'trade_history': [], 'cooldowns': {}}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def _journal_path():
    path = SIGNAL_JOURNAL_FILE
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def append_signal_journal(record: dict):
    """Append one JSON line to the signal journal (for accuracy eval)."""
    try:
        path = _journal_path()
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.warning(f"signal journal write failed: {e}")


def apply_slippage(price, side, is_buy_action, atr=0):
    """Adverse-only slippage on fills (entry and exit).

    side: position side 'BUY' (long) / 'SELL' (short) — for callers/clarity.
    is_buy_action: True = this fill buys (open long / close short) → pay higher;
                   False = this fill sells (open short / close long) → sell lower.
    Rules (bps from SLIPPAGE_BPS; optional atr*SLIPPAGE_ATR_FRAC):
      Open BUY / Close short: price * (1 + bps/10000) [+ atr*frac]
      Open SELL / Close long: price * (1 - bps/10000) [- atr*frac]
    """
    bps = float(SLIPPAGE_BPS) / 10000.0
    atr_pad = float(atr or 0) * float(SLIPPAGE_ATR_FRAC or 0)
    px = float(price)
    if is_buy_action:
        return px * (1.0 + bps) + atr_pad
    return px * (1.0 - bps) - atr_pad

def make_binance_spot_exchange():
    """Public spot via data-api.binance.vision (avoids api.binance.com 451)."""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'fetchMarkets': ['spot'],
            'fetchCurrencies': False,
        },
    })
    _pub = 'https://data-api.binance.vision'
    exchange.urls['api']['public'] = f'{_pub}/api/v3'
    exchange.urls['api']['private'] = f'{_pub}/api/v3'
    exchange.urls['api']['v1'] = f'{_pub}/api/v1'
    return exchange

def scan_and_trade_v2():
    logger.info(f"{'='*60}")
    logger.info(f"🚀 RegimeTrader AI v2 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if SIGNAL_OBSERVE_MODE:
        logger.info("📡 SIGNAL_OBSERVE_MODE=ON — journal only, no new opens")
    logger.info(f"{'='*60}")

    # 加载模型（优先 multi_full，缺失则回退 quantile）
    try:
        model_path = resolve_model_file()
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        # Silence RF/joblib Parallel spam on every predict
        if hasattr(model, 'verbose'):
            try:
                model.verbose = 0
            except Exception:
                pass
        logger.info(f"Model loaded from {model_path}")
    except Exception as e:
        logger.error(
            f"Model not found: {e}. Train with: python train_model_v2_multi.py "
            f"or python train_model_v2_quantile.py"
        )
        return

    # 加载状态
    state = load_state()
    balance = state['balance']
    positions = state['positions']
    signal_bars = state.setdefault('signal_bars', {})  # symbol -> last closed 1h bar iso used for entry
    logger.info(f"Balance: ${balance:.2f} | Positions: {len(positions)}")

    fee_rate = 0.0004
    exchange = make_binance_spot_exchange()

    # 1) 更新持仓（观察模式仍正常平仓）
    closed_positions = []
    unrealized_total = 0.0

    cooldowns = state.setdefault('cooldowns', {})
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    for sym, pos in list(positions.items()):
        try:
            ticker = exchange.fetch_ticker(sym)
            price = ticker['last']
            entry = pos['entry_price']
            amount = pos['amount']
            atr = pos['atr']
            sl = pos['sl']
            tp = pos.get('tp')

            exit_price = None
            exit_reason = None

            if pos['type'] == 'BUY':
                unreal = (price - entry) * amount
                unrealized_total += unreal
                one_r = atr * STOP_LOSS_ATR_MULT
                activate = entry + one_r * float(TRAIL_ACTIVATE_R)
                if price >= activate:
                    if price > pos.get('highest_seen', entry):
                        pos['highest_seen'] = price
                    # Trail + floor at breakeven once activated
                    pos['sl'] = max(sl, price - atr * TRAILING_STOP_ATR, entry)
                    sl = pos['sl']
                elif price > pos.get('highest_seen', entry):
                    pos['highest_seen'] = price
                # Prefer TP if hit; else trailing/fixed SL (same as before)
                if tp is not None and price >= tp:
                    exit_price = tp
                    exit_reason = 'TP'
                elif price <= sl:
                    exit_price = sl
                    exit_reason = 'SL/TRAIL'
                else:
                    try:
                        et = datetime.datetime.fromisoformat(str(pos.get('entry_time','')).replace('Z',''))
                        hold_h = (now_utc - et).total_seconds() / 3600.0
                        if hold_h >= float(MAX_HOLD_HOURS):
                            exit_price = price
                            exit_reason = 'MAX_HOLD'
                    except Exception:
                        pass
                if exit_price is not None:
                    exit_price = apply_slippage(exit_price, 'BUY', is_buy_action=False, atr=atr)
                    pnl = (exit_price - entry) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee, exit_reason))
                    logger.info(f"CLOSED LONG {sym} @{exit_price:.4f} ({exit_reason}) PnL:${pnl:.2f}")
            elif pos['type'] == 'SELL':
                unreal = (entry - price) * amount
                unrealized_total += unreal
                one_r = atr * STOP_LOSS_ATR_MULT
                activate = entry - one_r * float(TRAIL_ACTIVATE_R)
                if price <= activate:
                    if price < pos.get('lowest_seen', entry):
                        pos['lowest_seen'] = price
                    pos['sl'] = min(sl, price + atr * TRAILING_STOP_ATR, entry)
                    sl = pos['sl']
                elif pos.get('lowest_seen') is None or price < pos.get('lowest_seen', entry):
                    pos['lowest_seen'] = price
                if tp is not None and price <= tp:
                    exit_price = tp
                    exit_reason = 'TP'
                elif price >= sl:
                    exit_price = sl
                    exit_reason = 'SL/TRAIL'
                else:
                    try:
                        et = datetime.datetime.fromisoformat(str(pos.get('entry_time','')).replace('Z',''))
                        hold_h = (now_utc - et).total_seconds() / 3600.0
                        if hold_h >= float(MAX_HOLD_HOURS):
                            exit_price = price
                            exit_reason = 'MAX_HOLD'
                    except Exception:
                        pass
                if exit_price is not None:
                    exit_price = apply_slippage(exit_price, 'SELL', is_buy_action=True, atr=atr)
                    pnl = (entry - exit_price) * amount
                    fee = (exit_price * amount) * fee_rate
                    balance += pos['margin'] + pnl - fee
                    closed_positions.append((sym, pnl, fee, exit_reason))
                    logger.info(f"CLOSED SHORT {sym} @{exit_price:.4f} ({exit_reason}) PnL:${pnl:.2f}")
        except Exception as e:
            logger.warning(f"{sym} update error: {e}")

    # 记录平仓历史 + 写入 per-symbol 冷却
    for item in closed_positions:
        sym, pnl, fee = item[0], item[1], item[2]
        exit_reason = item[3] if len(item) > 3 else 'SL/TRAIL'
        positions.pop(sym, None)
        exit_iso = now_utc.isoformat() + 'Z'
        state['trade_history'].append({
            'symbol': sym,
            'pnl': pnl,
            'fee': fee,
            'exit_time': exit_iso,
            'reason': exit_reason,
        })
        # Cooldown: block re-entry for COOLDOWN_HOURS after close
        cooldowns[sym] = exit_iso

    # 2) 计算总权益
    margin_used = sum(p['margin'] for p in positions.values())
    total_equity = balance + margin_used + unrealized_total
    logger.info(f"Equity: ${total_equity:.2f} | Cash: ${balance:.2f} | Margin: ${margin_used:.2f}")

    # Weird equity/cash: cash ~0 while margin fully tied up → do not open more
    can_open_new = True
    if balance <= 1e-6 and margin_used > 0:
        can_open_new = False
        logger.warning(
            f"Cash~0 with margin in use (${margin_used:.2f}) — skip new opens "
            f"(manage existing only)"
        )
    if total_equity <= 0:
        can_open_new = False
        logger.warning(f"Equity <= 0 (${total_equity:.2f}) — skip new opens")

    # 3) 宏观风险检查（临时禁用）
    adjusted_risk_pct = RISK_PER_TRADE_PCT

    # 4) 扫描新机会 / 记 journal
    logger.info(f"Scanning symbols (TRADING_SYMBOLS whitelist / top {SCAN_LIMIT})...")
    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers()
        usdt_pairs = [s for s, t in tickers.items() if s.endswith('/USDT') and 'UP/' not in s and 'DOWN/' not in s]
        usdt_pairs.sort(key=lambda s: (tickers[s].get('quoteVolume') or 0), reverse=True)

        # 白名单锁定训练集币种；空列表则扫 top SCAN_LIMIT
        if TRADING_SYMBOLS:
            symbols = list(TRADING_SYMBOLS)
            logger.info(f"白名单锁定: {symbols}")
        else:
            symbols = usdt_pairs[:SCAN_LIMIT]
    except Exception as e:
        logger.error(f"Fetch tickers failed: {e}")
        symbols = list(TRADING_SYMBOLS) if TRADING_SYMBOLS else []

    new_entries = []
    observed_signals = []

    def _in_cooldown(sym: str) -> bool:
        until = cooldowns.get(sym)
        if not until:
            return False
        try:
            closed_at = datetime.datetime.fromisoformat(until.replace('Z', ''))
        except Exception:
            return False
        hours = (now_utc - closed_at).total_seconds() / 3600.0
        return hours < float(COOLDOWN_HOURS)

    for symbol in symbols:
        time.sleep(0.2)

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp','Open','High','Low','Close','Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            if len(df) < 200:
                continue

            # 1h 模型：默认丢掉未收盘的最后一根，用已收盘 K 做特征/置信度
            bar_for_signal = df.index[-1]
            if ENTRY_ON_CLOSED_1H_ONLY and len(df) >= 2:
                last_open = df.index[-1].to_pydatetime()
                # Binance 1h bar open time; treat as forming if now < open+1h
                if (now_utc - last_open).total_seconds() < 3600 - 5:
                    df = df.iloc[:-1]
                    bar_for_signal = df.index[-1]

            df_feat = prepare_features_v2(df.copy())
            if df_feat.empty:
                continue

            latest = df_feat.iloc[-1]
            bar_for_signal = latest.name
            bar_key = bar_for_signal.isoformat() if hasattr(bar_for_signal, 'isoformat') else str(bar_for_signal)
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

            pred = int(model.predict(X)[0])
            probs = model.predict_proba(X)[0]
            confidence = float(probs[pred])
            adx = float(latest['ADX'])

            # 信号判断 + DI 方向过滤（BUY 需 +DI>-DI；SELL 需 -DI>+DI）
            plus_di = float(latest['+DI'])
            minus_di = float(latest['-DI'])
            close_px = float(latest['Close'])
            class_name = CLASS_NAMES.get(pred, str(pred))

            di_abs = abs(float(plus_di) - float(minus_di))
            gates_passed = (
                adx >= ADX_STRONG_THRESHOLD
                and confidence >= CONFIDENCE_THRESHOLD
                and di_abs >= float(MIN_DI_DIFF)
            )
            proposed_signal = None
            if gates_passed:
                if pred == 2 and plus_di > minus_di:
                    proposed_signal = "BUY"
                elif pred == 0 and minus_di > plus_di:
                    proposed_signal = "SELL"
            # gates_passed means ADX+conf; proposed_signal also needs DI agree
            entry_gates_ok = proposed_signal is not None

            ts_iso = now_utc.isoformat() + 'Z'
            # Journal every scanned whitelist symbol (always)
            append_signal_journal({
                'timestamp': ts_iso,
                'symbol': symbol,
                'pred': pred,
                'class_name': class_name,
                'confidence': confidence,
                'adx': adx,
                'plus_di': plus_di,
                'minus_di': minus_di,
                'close': close_px,
                'proposed_signal': proposed_signal,
                'gates_passed': entry_gates_ok,
                'closed_1h_bar': bar_key if ENTRY_ON_CLOSED_1H_ONLY else None,
                'adx_conf_ok': gates_passed,
                'observe_mode': bool(SIGNAL_OBSERVE_MODE),
            })

            signal = proposed_signal  # candidate for open

            # Skip open if already holding this symbol
            if symbol in positions:
                signal = None

            if signal and _in_cooldown(symbol):
                logger.debug(f"Skip {symbol}: cooldown ({COOLDOWN_HOURS}h / {MIN_BARS_BETWEEN_TRADES} bars)")
                signal = None

            # 最大同时持仓限制
            if signal and len(positions) >= MAX_CONCURRENT_POSITIONS:
                logger.debug(
                    f"Skip {symbol} {signal}: max concurrent positions "
                    f"({MAX_CONCURRENT_POSITIONS})"
                )
                signal = None

            if signal and not can_open_new:
                logger.debug(f"Skip {symbol} {signal}: cash/equity guard")
                signal = None


            # 同一根已收盘 1h K 只评估/开仓一次（5min 扫描去重）
            if signal and ENTRY_ON_CLOSED_1H_ONLY:
                if signal_bars.get(symbol) == bar_key:
                    signal = None
                elif not SIGNAL_OBSERVE_MODE:
                    # reserve bar on actual open below; mark when we attempt entry
                    pass

            if signal and SIGNAL_OBSERVE_MODE:
                logger.info(
                    f"SIGNAL_OBSERVE {signal} {symbol} @{close_px:.4f} "
                    f"pred={pred}({class_name}) conf={confidence:.3f} "
                    f"ADX={adx:.1f} +DI={plus_di:.1f} -DI={minus_di:.1f}"
                )
                observed_signals.append(f"{symbol} {signal} @{close_px:.4f}")
                continue  # do not mutate balance/positions

            if signal:
                atr = float(latest['ATR'])
                # Adverse slippage on fill; SL/TP anchored to slipped entry
                entry_price = apply_slippage(
                    close_px, signal, is_buy_action=(signal == "BUY"), atr=atr
                )

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
                free_cash = balance
                # Cap single-position margin so one fill cannot consume all cash
                max_margin = min(
                    free_cash,
                    total_equity * float(MAX_MARGIN_PCT_OF_EQUITY),
                    max(0.0, total_equity - used_margin),
                )
                if max_margin <= 1e-6:
                    logger.info(
                        f"Skip {symbol} {signal}: no free margin "
                        f"(cash ${free_cash:.2f}, used ${used_margin:.2f})"
                    )
                    continue
                if margin_req > max_margin:
                    scale = max_margin / margin_req
                    amount *= scale
                    margin_req = max_margin
                    logger.info(
                        f"Size {symbol} {signal}: scaled to margin "
                        f"${margin_req:.2f} ({float(MAX_MARGIN_PCT_OF_EQUITY)*100:.0f}% equity / cash cap)"
                    )

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
                    'entry_time': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z',
                    'confidence': confidence
                }
                positions[symbol] = pos
                if ENTRY_ON_CLOSED_1H_ONLY:
                    signal_bars[symbol] = bar_key
                new_entries.append(f"{symbol} {signal} @{entry_price:.4f} SL:{sl_price:.4f}")
                logger.info(f"NEW {signal} {symbol} @{entry_price:.4f} | ATR:{atr:.4f} Amount:{amount:.4f}")

        except Exception as e:
            logger.warning(f"{symbol} scan error: {e}")

    # 4) 保存状态
    state['balance'] = balance
    state['positions'] = positions
    state['cooldowns'] = cooldowns
    state['signal_bars'] = signal_bars
    save_state(state)

    # 5) 输出摘要
    logger.info(f"\n--- Summary ---")
    logger.info(f"Equity: ${total_equity:.2f} ({((total_equity/10000)-1)*100:+.1f}%)")
    logger.info(f"Closed positions: {len(closed_positions)}")
    for item in closed_positions:
        sym, pnl = item[0], item[1]
        reason = item[3] if len(item) > 3 else ''
        logger.info(f"  {sym}: ${pnl:+.2f} {reason}")
    if SIGNAL_OBSERVE_MODE:
        logger.info(f"Observed (not opened): {len(observed_signals)}")
        for e in observed_signals:
            logger.info(f"  {e}")
        logger.info(f"New entries: 0 (SIGNAL_OBSERVE_MODE)")
    else:
        logger.info(f"New entries: {len(new_entries)}")
        for e in new_entries:
            logger.info(f"  {e}")

if __name__ == '__main__':
    scan_and_trade_v2()
