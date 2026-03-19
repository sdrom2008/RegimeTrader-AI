#!/usr/bin/env python3
"""
RegimeTrader AI - Performance Analyzer
生成详细的交易绩效报告
"""

import os
import json
import datetime
import ccxt
from pathlib import Path
import shutil

WORKSPACE = Path(__file__).parent
# 支持 v1 和 v2 状态文件
import os
STATE_FILE_V1 = Path('/home/sdrom2008/.openclaw/workspace/paper_trade_state.json')
STATE_FILE_V2 = Path('/home/sdrom2008/.openclaw/workspace/regime_trader_ai_product/paper_trade_state_v2.json')
STATE_FILE = Path(os.environ.get('STATE_FILE', str(STATE_FILE_V2 if STATE_FILE_V2.exists() else STATE_FILE_V1)))
LOGS_DIR = WORKSPACE / 'logs' / 'performance'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def load_state():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def fetch_current_prices():
    ex = ccxt.binance({'enableRateLimit': True})
    prices = {}
    for symbol in state['positions']:
        try:
            prices[symbol] = ex.fetch_ticker(symbol)['last']
        except:
            prices[symbol] = None
    return prices

def calculate_metrics(state, prices):
    balance = state['balance']
    positions = state['positions']
    history = state.get('trade_history', [])

    # 当前持仓数据
    total_margin = sum(p['margin'] for p in positions.values())
    unrealized = 0
    position_details = []
    for sym, pos in positions.items():
        cur = prices.get(sym)
        if cur is None:
            continue
        if pos['type'] == 'BUY':
            pnl = (cur - pos['entry_price']) * pos['amount']
        else:
            pnl = (pos['entry_price'] - cur) * pos['amount']
        unrealized += pnl
        position_details.append({
            'symbol': sym,
            'type': pos['type'],
            'amount': pos['amount'],
            'entry': pos['entry_price'],
            'current': cur,
            'unreal': pnl,
            'margin': pos['margin'],
            'sl': pos['sl'],
            'entry_time': pos['entry_time']
        })

    # 已平仓交易统计
    closed_trades = []
    total_pnl = 0
    total_fee = 0
    winning_trades = []
    losing_trades = []
    for t in history:
        pnl = t['pnl']
        fee = t.get('fee', 0)
        total_pnl += pnl
        total_fee += fee
        closed_trades.append({
            'symbol': t['symbol'],
            'pnl': pnl,
            'fee': fee,
            'exit_time': t.get('exit_time')
        })
        if pnl > 0:
            winning_trades.append(pnl)
        else:
            losing_trades.append(pnl)

    num_trades = len(closed_trades) + len(positions)  # 计算时包括未平仓
    num_closed = len(closed_trades)
    num_win = len(winning_trades)
    num_loss = len(losing_trades)

    win_rate = num_win / num_closed if num_closed > 0 else 0

    avg_win = sum(winning_trades) / num_win if num_win > 0 else 0
    avg_loss = abs(sum(losing_trades) / num_loss) if num_loss > 0 else 0
    avg_win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

    total_realized_pnl = sum(t['pnl'] for t in closed_trades)
    total_realized_fee = sum(t.get('fee',0) for t in closed_trades)
    total_commission = total_fee + total_realized_fee

    total_equity = balance + total_margin + unrealized
    initial_capital = 10000.0
    total_return = (total_equity - initial_capital) / initial_capital * 100

    # 最大回撤（简化：基于当前总资产峰值）
    # TODO: 记录历史峰值更精确
    max_drawdown = max(0, (initial_capital - total_equity) / initial_capital * 100) if total_equity < initial_capital else 0

    # 期望值
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss if avg_loss > 0 else 0

    return {
        'summary': {
            'initial_capital': initial_capital,
            'total_equity': total_equity,
            'balance': balance,
            'total_margin': total_margin,
            'unrealized_pnl': unrealized,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_drawdown,
            'expectancy': expectancy
        },
        'trades': {
            'num_closed': num_closed,
            'num_open': len(positions),
            'num_total': num_closed + len(positions),
            'num_win': num_win,
            'num_loss': num_loss,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_loss_ratio': avg_win_loss_ratio,
            'total_realized_pnl': total_realized_pnl,
            'total_commission': total_commission
        },
        'positions': position_details,
        'closed_trades': closed_trades
    }

def generate_markdown_report(metrics, report_time):
    lines = []
    lines.append(f"# RegimeTrader AI - 绩效报告")
    lines.append(f"**报告时间:** {report_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"**数据来源:** `paper_trade_state.json`")
    lines.append("")

    # 总览
    s = metrics['summary']
    lines.append("## 📈 核心指标")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 初始资金 | ${s['initial_capital']:,.2f} |")
    lines.append(f"| 总资产 | ${s['total_equity']:,.2f} |")
    lines.append(f"| 余额 | ${s['balance']:,.2f} |")
    lines.append(f"| 保证金占用 | ${s['total_margin']:,.2f} |")
    lines.append(f"| 未实现盈亏 | ${s['unrealized_pnl']:,.2f} |")
    lines.append(f"| 总收益率 | {s['total_return_pct']:.2f}% |")
    lines.append(f"| 最大回撤 | {s['max_drawdown_pct']:.2f}% |")
    lines.append(f"| 期望值 | ${s['expectancy']:,.2f} |")
    lines.append("")

    # 交易统计
    t = metrics['trades']
    lines.append("## 📊 交易统计")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总交易次数 (已平+未平) | {t['num_total']} |")
    lines.append(f"| 已平仓 | {t['num_closed']} |")
    lines.append(f"| 当前持仓 | {t['num_open']} |")
    lines.append(f"| 胜率 | {t['win_rate']*100:.1f}% |")
    lines.append(f"| 平均盈利 | ${t['avg_win']:,.2f} |")
    lines.append(f"| 平均亏损 | ${t['avg_loss']:,.2f} |")
    lines.append(f"| 盈亏比 | {t['avg_win_loss_ratio']:.2f} |")
    lines.append(f"| 已实现总盈亏 | ${t['total_realized_pnl']:,.2f} |")
    lines.append(f"| 手续费总额 | ${t['total_commission']:,.2f} |")
    lines.append("")

    # 持仓详情
    if metrics['positions']:
        lines.append("## 🔍 当前持仓")
        lines.append("| 币对 | 方向 | 数量 | 开仓价 | 当前价 | 未实现盈亏 | 止损价 |")
        lines.append("|------|------|------|--------|--------|------------|--------|")
        for p in metrics['positions']:
            lines.append(f"| {p['symbol']} | {p['type']} | {p['amount']:,.0f} | {p['entry']:.4f} | {p['current']:.4f} | ${p['unreal']:,.2f} | {p['sl']:.4f} |")
        lines.append("")

    # 已平仓记录
    if metrics['closed_trades']:
        lines.append("## ✅ 已平仓交易")
        lines.append("| 币对 | 盈亏($) | 手续费($) | 平仓时间 |")
        lines.append("|------|----------|------------|----------|")
        for t in metrics['closed_trades']:
            exit_time = t['exit_time'][:19].replace('T', ' ') if t.get('exit_time') else '-'
            lines.append(f"| {t['symbol']} | ${t['pnl']:,.2f} | ${t['fee']:,.2f} | {exit_time} |")
        lines.append("")

    # 资产曲线（简略）
    lines.append("## 📉 资产变化")
    lines.append(f"**当前总资产** ${s['total_equity']:,.2f} （初始: ${s['initial_capital']:,.2f}）")
    lines.append("")

    return "\n".join(lines)

def save_report(md_content, report_time):
    filename = LOGS_DIR / f"performance_{report_time.strftime('%Y%m%d_%H%M')}.md"
    with open(filename, 'w') as f:
        f.write(md_content)
    return filename

def send_whatsapp_alert(message):
    """发送 WhatsApp 通知（使用 openclaw CLI）"""
    print(f"[WhatsApp] {message}")
    safe_msg = message.replace("'", "'\\''")
    target_number = "+8613908412393"
    openclaw_path = "/home/sdrom2008/.npm-global/bin/openclaw"
    # Verify the executable exists
    if not os.path.exists(openclaw_path):
        openclaw_path = shutil.which("openclaw") or "openclaw"
    cmd = f"{openclaw_path} message send --channel whatsapp --target '{target_number}' --message '{safe_msg}'"
    try:
        import subprocess
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"[WhatsApp] Sent")
    except Exception as e:
        print(f"[WhatsApp] Failed: {e}")

if __name__ == "__main__":
    report_time = datetime.datetime.now(datetime.timezone.utc)
    state = load_state()
    prices = fetch_current_prices()
    metrics = calculate_metrics(state, prices)
    md = generate_markdown_report(metrics, report_time)
    filepath = save_report(md, report_time)

    # 发送 WhatsApp 摘要
    s = metrics['summary']
    t = metrics['trades']
    summary_msg = (
        f"📊 绩效报告\n"
        f"🕒 {report_time.strftime('%H:%M')} UTC\n"
        f"💰 总资产: ${s['total_equity']:,.2f} ({s['total_return_pct']:+.2f}%)\n"
        f"📈 交易次数: {t['num_total']} | 胜率: {t['win_rate']*100:.0f}%\n"
        f"🤑 已实现盈亏: ${t['total_realized_pnl']:,.2f}\n"
        f"📦 当前持仓: {t['num_open']} | 未实现盈亏: ${s['unrealized_pnl']:,.2f}"
    )
    send_whatsapp_alert(summary_msg)

    print(f"✅ 绩效报告已生成: {filepath}")
