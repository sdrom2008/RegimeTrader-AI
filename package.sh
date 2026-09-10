#!/bin/bash
# 打包 RegimeTrader AI 产品
# 用法: ./package.sh [输出文件名]

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PRODUCT_DIR="RegimeTrader-AI"
OUTPUT="${1:-regimetrader_ai_product_$(date +%Y%m%d_%H%M).tar.gz}"

TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/$PRODUCT_DIR"
# Copy tracked-ish sources; exclude venv, data, pkl, git
rsync -a --exclude '.venv' --exclude 'venv' --exclude '.git' \
  --exclude 'data' --exclude '*.pkl' --exclude '__pycache__' \
  --exclude 'logs' --exclude 'paper_trade_state*.json' \
  "$ROOT/" "$TMPDIR/$PRODUCT_DIR/"

tar -czf "$OUTPUT" -C "$TMPDIR" "$PRODUCT_DIR"
rm -rf "$TMPDIR"
echo "✅ 产品已打包: $OUTPUT"
echo "   包含: $PRODUCT_DIR/ (无 data/、*.pkl、.venv)"
