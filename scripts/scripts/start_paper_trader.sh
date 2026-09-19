#!/bin/bash
# 启动 DRY_RUN live_executor 常驻进程（正确入口，非单次 paper_trader.py）
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec "$ROOT/start.sh" dry bg
