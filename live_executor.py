#!/usr/bin/env python3
"""
RegimeTrader AI - 主执行入口（v2 版本）
用法：STRATEGY_VERSION=v2 DRY_RUN=1 python live_executor.py
"""

import os
import sys
import time
import datetime
from pathlib import Path

# 确保导入当前目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SCAN_INTERVAL,  # 扫描间隔（秒）
)

def main():
    """
    主循环：
    - 每 SCAN_INTERVAL 秒执行一次扫描
    - 调用 paper_trader.scan_and_trade_v2()
    - 处理异常并记录日志
    """
    print(f"\n{'='*60}")
    print(f"🚀 RegimeTrader AI - Live Executor (v2)")
    print(f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Strategy: v2 (三分类 + 宏观风险监控)")
    print(f"{'='*60}\n")

    # 导入执行器（延迟导入，确保配置加载）
    from paper_trader import scan_and_trade_v2

    interval = SCAN_INTERVAL

    print(f"[*] Scan interval: {interval} seconds")
    print("[*] Starting main loop...\n")

    while True:
        try:
            scan_and_trade_v2()
        except Exception as e:
            print(f"[!] Executor error: {e}")
            import traceback
            traceback.print_exc()

        # 等待下一轮
        time.sleep(interval)

if __name__ == '__main__':
    main()
