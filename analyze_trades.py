import json
from datetime import datetime

with open('/home/sdrom2008/.openclaw/workspace/paper_trade_state.json', 'r') as f:
    state = json.load(f)

history = state.get('trade_history', [])
positions = state.get('positions', {})

print("=== 历史交易分析 ===\n")

# Group trades by symbol
symbols = {}
for trade in history:
    sym = trade['symbol']
    if sym not in symbols:
        symbols[sym] = []
    symbols[sym].append(trade)

# Summary per symbol
print("按币对统计:")
print(f"{'币对':<12} {'交易次数':<8} {'胜率':<8} {'总盈亏':<12} {'平均盈亏':<12} {'最大盈利':<12} {'最大亏损':<12}")
print("-"*80)
for sym, trades in sorted(symbols.items()):
    total = len(trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = total - wins
    win_rate = wins / total if total > 0 else 0
    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / total if total > 0 else 0
    max_win = max((t['pnl'] for t in trades), default=0)
    max_loss = min((t['pnl'] for t in trades), default=0)
    print(f"{sym:<12} {total:<8} {win_rate:>6.1%} ${total_pnl:>+9.2f} ${avg_pnl:>+9.2f} ${max_win:>9.2f} ${max_loss:>9.2f}")

# Overall stats
total_trades = len(history)
total_wins = sum(1 for t in history if t['pnl'] > 0)
overall_win_rate = total_wins / total_trades if total_trades > 0 else 0
total_pnl_all = sum(t['pnl'] for t in history)
avg_pnl_all = total_pnl_all / total_trades if total_trades > 0 else 0

print(f"\n总体统计:")
print(f"  总交易次数: {total_trades}")
print(f"  胜率: {overall_win_rate:.1%}")
print(f"  总盈亏: ${total_pnl_all:+.2f}")
print(f"  平均盈亏: ${avg_pnl_all:+.2f}")
print(f"  总手续费: ${sum(t['fee'] for t in history):.2f}")

# Current positions
print(f"\n当前持仓: {len(positions)} 个")
for sym, pos in positions.items():
    print(f"  {sym}: {pos['type']} 数量={pos['amount']:,.0f} 开仓={pos['entry_price']:.4f} margin=${pos['margin']:.2f}")
