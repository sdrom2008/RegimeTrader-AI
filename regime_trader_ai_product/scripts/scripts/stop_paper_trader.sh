#!/bin/bash
# 停止模拟盘常驻进程
if [ -f /tmp/paper_trader.pid ]; then
    kill $(cat /tmp/paper_trader.pid) && echo "✅ Paper trader stopped."
    rm -f /tmp/paper_trader.pid
else
    echo "ℹ️ No PID file, trying to kill by name..."
    pkill -f "paper_trader.py"
fi
