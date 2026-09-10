#!/bin/bash
# 启动模拟盘常驻进程
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p logs
PYTHON="${ROOT}/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="${ROOT}/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"
nohup "$PYTHON" paper_trader.py > logs/paper_trader_manual.log 2>&1 &
echo $! > /tmp/paper_trader.pid
echo "✅ Paper trader started (PID $(cat /tmp/paper_trader.pid))"
