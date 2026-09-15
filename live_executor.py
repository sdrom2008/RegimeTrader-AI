#!/usr/bin/env python3
"""
RegimeTrader AI - 主执行入口（v2 版本）
用法：STRATEGY_VERSION=v2 DRY_RUN=1 python live_executor.py
"""

import os
import sys
import time
import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 确保导入当前目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SCAN_INTERVAL,  # 扫描间隔（秒）
)

def _file_mtime(path: str):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def main():
    """
    主循环：
    - 每 SCAN_INTERVAL 秒执行一次扫描
    - 调用 paper_trader.scan_and_trade_v2()
    - 处理异常并记录日志
    - 仅当 config/paper_trader 文件 mtime 变化时 reload（避免每轮重载 170MB+ 模型）
    """
    print(f"\n{'='*60}")
    print(f"🚀 RegimeTrader AI - Live Executor (v2)")
    print(f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Strategy: v2 (三分类 + 宏观风险监控)")
    print(f"{'='*60}\n")

    import importlib
    import config as _cfg
    import paper_trader as _pt

    interval = SCAN_INTERVAL
    repo = os.path.dirname(os.path.abspath(__file__))
    watch = {
        'config': os.path.join(repo, 'config.py'),
        'paper_trader': os.path.join(repo, 'paper_trader.py'),
    }
    last_mtimes = {k: _file_mtime(p) for k, p in watch.items()}

    print(f"[*] Scan interval: {interval} seconds")
    print("[*] Starting main loop (reload only when config/paper_trader mtime changes)...\n")

    heartbeat_path = os.path.join(repo, 'logs', 'executor_heartbeat.json')

    def _write_heartbeat(phase: str, extra=None):
        payload = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'phase': phase,
            'pid': os.getpid(),
        }
        if extra:
            payload.update(extra)
        try:
            os.makedirs(os.path.dirname(heartbeat_path), exist_ok=True)
            with open(heartbeat_path, 'w', encoding='utf-8') as hf:
                import json as _json
                _json.dump(payload, hf)
        except Exception as he:
            print(f"[!] heartbeat write failed: {he}")

    while True:
        try:
            changed = []
            for key, path in watch.items():
                mt = _file_mtime(path)
                if mt is not None and mt != last_mtimes.get(key):
                    changed.append(key)
                    last_mtimes[key] = mt
            if changed:
                print(f"[*] Hot-reload: {', '.join(changed)}")
                if 'config' in changed:
                    importlib.reload(_cfg)
                if 'paper_trader' in changed or 'config' in changed:
                    # paper_trader imports config at load; reload after config
                    importlib.reload(_pt)
                interval = getattr(_cfg, "SCAN_INTERVAL", interval)
            _write_heartbeat('scan_start')
            t0 = time.time()
            _pt.scan_and_trade_v2()
            dt = time.time() - t0
            print(f"[*] Scan done in {dt:.1f}s")
            snap = getattr(_pt, 'LAST_SCAN_SNAPSHOT', None) or {}
            hb_extra = {'scan_seconds': round(dt, 2)}
            for k in (
                'equity', 'balance', 'positions', 'actionable',
                'max_adx', 'max_di', 'max_conf', 'ret_pct', 'quiet',
                'fail_adx', 'fail_conf', 'fail_di',
                'last_trade_iso', 'idle_hours_since_last_trade',
            ):
                if k in snap:
                    hb_extra[k] = snap[k]
            _write_heartbeat('scan_done', hb_extra)
            if dt > max(60.0, float(interval) * 0.8):
                print(f"[!] Slow scan: {dt:.1f}s (interval={interval}s)")
        except Exception as e:
            print(f"[!] Executor error: {e}")
            import traceback
            traceback.print_exc()
            _write_heartbeat('error', {'error': str(e)[:200]})

        # 等待下一轮
        time.sleep(interval)

if __name__ == '__main__':
    main()
