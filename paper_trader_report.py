#!/usr/bin/env python3
import os
import json
import subprocess
from datetime import datetime, timezone
import sys

# Resolve workspace root
workspace_root = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(workspace_root, 'paper_trade_state.json')
LOG_FILE = os.path.join(workspace_root, 'logs', 'paper_trader_report.log')

def send_whatsapp_alert(message):
    print(f"[WhatsApp] {message}")
    safe_msg = message.replace("'", "'\\''")
    target_number = "+8613908412393"
    openclaw_path = "/home/sdrom2008/.npm-global/bin/openclaw"
    cmd = f"{openclaw_path} message send --channel whatsapp --target '{target_number}' --message '{safe_msg}'"
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"[WhatsApp] Success")
    except subprocess.CalledProcessError as e:
        print(f"[WhatsApp] Failed (exit {e.returncode}): {e.stderr}")
    except Exception as e:
        print(f"[WhatsApp] Exception: {e}")

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading state: {e}")
        return None

def format_float(f):
    return f"{f:.2f}" if f is not None else "N/A"

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    now = datetime.now(timezone.utc)
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S UTC')
    today_date = now.date()

    state = load_state()
    if state is None:
        msg = f"⚠️ 模拟盘报告：未找到状态文件。"
        print(msg)
        with open(LOG_FILE, 'a') as f: f.write(f"[{timestamp}] {msg}\n")
        send_whatsapp_alert(msg)
        return

    capital = state.get('capital', 0)
    positions = state.get('positions', {})
    trade_history = state.get('trade_history', [])

    # Compute today's trades and P&L
    today_trades = []  # both closed and open but opened today
    today_realized_pnl = 0.0
    today_unrealized_pnl = 0.0
    today_positions = []

    # 1. Closed trades that exited today
    for trade in trade_history:
        exit_str = trade.get('exit_time')
        if exit_str:
            try:
                exit_dt = datetime.fromisoformat(exit_str.replace('Z', '+00:00'))
                if exit_dt.date() == today_date:
                    today_trades.append(trade)
                    today_realized_pnl += trade.get('pnl', 0)
            except Exception:
                pass

    # 2. Open positions that opened today
    import ccxt
    exchange = ccxt.binance({'enableRateLimit': True})
    for sym, pos in positions.items():
        entry_str = pos.get('entry_time')
        if entry_str:
            try:
                entry_dt = datetime.fromisoformat(entry_str.replace('Z', '+00:00'))
                if entry_dt.date() == today_date:
                    today_positions.append(sym)
                    # Calculate unrealized
                    ticker = exchange.fetch_ticker(sym)
                    price = ticker['last']
                    ptype = pos.get('type')
                    entry = pos.get('entry_price', 0)
                    amount = pos.get('amount', 0)
                    if ptype == 'BUY':
                        unrealized = (price - entry) * amount
                    elif ptype == 'SELL':
                        unrealized = (entry - price) * amount
                    else:
                        unrealized = 0
                    today_unrealized_pnl += unrealized
            except Exception:
                pass

    today_total_pnl = today_realized_pnl + today_unrealized_pnl

    # Build report
    report_lines = [
        f"📊 模拟盘每小时报告",
        f"🕒 时间: {timestamp}",
        f"💰 总资产: ${format_float(capital)} USDT",
        f"📦 当前持仓: {len(positions)} 个",
    ]

    if positions:
        for sym, pos in positions.items():
            pos_type = pos.get('type', '?')
            entry = pos.get('entry_price', 0)
            amount = pos.get('amount', 0)
            margin = pos.get('margin', 0)
            try:
                ticker = exchange.fetch_ticker(sym)
                current_price = ticker['last']
                if pos_type == 'BUY':
                    unrealized = (current_price - entry) * amount
                elif pos_type == 'SELL':
                    unrealized = (entry - current_price) * amount
                else:
                    unrealized = 0
                report_lines.append(f"  • {sym} {pos_type} 开仓价:${entry:.4f} 数量:{amount:.4f} 保证金:${margin:.2f} 浮盈/浮亏:${unrealized:.2f}")
            except Exception as e:
                report_lines.append(f"  • {sym} {pos_type} (获取价格出错: {e})")
    else:
        report_lines.append("  • 暂无持仓。")

    report_lines.append(f"📅 今日开仓: {len(today_positions)} 个 ({', '.join(today_positions) if today_positions else '无'})")
    report_lines.append(f"📈 今日总盈亏（含浮盈）: ${format_float(today_total_pnl)}")

    report_msg = "\n".join(report_lines)

    # Log and send
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] Report: Capital=${capital}, Positions={len(positions)}, Today P&L=${today_total_pnl}\n")
    send_whatsapp_alert(report_msg)

if __name__ == "__main__":
    main()
