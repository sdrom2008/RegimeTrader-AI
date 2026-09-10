#!/bin/bash
# RegimeTrader AI 快速启动脚本
# 用法: ./start.sh [dry|live]

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODE="${1:-dry}"

# Prefer local .venv, then venv, then python3
if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
    PYTHON="$ROOT/venv/bin/python"
else
    PYTHON="python3"
fi

if [ "$MODE" = "dry" ]; then
    echo "🧪 启动模拟盘（DRY_RUN=1）..."
    DRY_RUN=1 "$PYTHON" live_executor.py
elif [ "$MODE" = "live" ]; then
    echo "🔥 启动实盘（DRY_RUN=0）... 注意：将执行真实订单！"
    read -p "确认已小资金测试且理解风险？(yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        DRY_RUN=0 "$PYTHON" live_executor.py
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
