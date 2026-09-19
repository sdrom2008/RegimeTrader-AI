#!/bin/bash
# 前台跑 live_executor；默认 DRY_RUN=1（避免误触实盘）
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="${ROOT}/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"
export DRY_RUN="${DRY_RUN:-1}"
exec "$PYTHON" -u live_executor.py
