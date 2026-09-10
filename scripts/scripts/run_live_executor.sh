#!/bin/bash
# 手动运行一次实盘脚本（用于测试）
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="${ROOT}/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"
"$PYTHON" live_executor.py
