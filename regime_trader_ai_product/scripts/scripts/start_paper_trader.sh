#!/bin/bash
# 启动模拟盘常驻进程
cd /home/sdrom2008/.openclaw/workspace/regime_trader_ai_product
nohup /home/sdrom2008/.openclaw/workspace/.venv/bin/python paper_trader.py > ../logs/paper_trader_manual.log 2>&1 &
echo $! > /tmp/paper_trader.pid
echo "✅ Paper trader started (PID $(cat /tmp/paper_trader.pid))"
