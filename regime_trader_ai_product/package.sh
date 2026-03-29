#!/bin/bash
# 打包 RegimeTrader AI 产品
# 用法: ./package.sh [输出文件名]

PRODUCT_DIR="regime_trader_ai_product"
OUTPUT="${1:-regimetrader_ai_product_$(date +%Y%m%d_%H%M).tar.gz}"

# 临时目录
TMPDIR=$(mktemp -d)
cp -r $PRODUCT_DIR "$TMPDIR/"

# 清理缓存和日志
rm -rf "$TMPDIR/$PRODUCT_DIR/__pycache__"
rm -f "$TMPDIR/$PRODUCT_DIR/paper_trade_state.json"
rm -rf "$TMPDIR/$PRODUCT_DIR/logs/*"

# 创建压缩包
tar -czf $OUTPUT -C $TMPDIR $PRODUCT_DIR

echo "✅ 产品已打包: $OUTPUT"
echo "   包含: $PRODUCT_DIR/"
echo "   已清理: 缓存、日志、状态文件"
