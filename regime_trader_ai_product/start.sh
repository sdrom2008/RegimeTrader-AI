#!/bin/bash
# RegimeTrader AI 快速启动脚本
# 用法: ./start.sh [dry|live]

set -e

cd "$(dirname "$0")"

MODE="${1:-dry}"

if [ "$MODE" = "dry" ]; then
    echo "🧪 启动模拟盘（DRY_RUN=1）..."
    DRY_RUN=1 /home/sdrom2008/.openclaw/workspace/regime_trader_ai_product/venv/bin/python -m regime_trader_ai_product.live_executor
elif [ "$MODE" = "live" ]; then
    echo "🔥 启动实盘（DRY_RUN=0）... 注意：将执行真实订单！"
    read -p "确认已小资金测试且理解风险？(yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        DRY_RUN=0 /home/sdrom2008/.openclaw/workspace/regime_trader_ai_product/venv/bin/python -m regime_trader_ai_product.live_executor
    else
        echo "取消启动"
        exit 1
    fi
else
    echo "用法: $0 [dry|live]"
    echo "  dry - 模拟盘（默认）"
    echo "  live - 实盘"
    exit 1
fi
