#!/usr/bin/env python3
"""
RegimeTrader AI - 主执行入口（v2 版本）
用法：STRATEGY_VERSION=v2 DRY_RUN=1 python live_executor.py
"""

import os
import sys
import time
import datetime
import concurrent.futures
import atexit
import signal

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

# Hard cap so a hung ccxt/DNS call cannot freeze the loop for hours.
SCAN_HARD_TIMEOUT_SEC = float(os.environ.get('SCAN_HARD_TIMEOUT_SEC', '90'))
# Keep heartbeat fresh while sleeping between scans (detect stalls externally).
SLEEP_HEARTBEAT_SEC = float(os.environ.get('SLEEP_HEARTBEAT_SEC', '60'))


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
    - scan hard-timeout + chunked sleep heartbeats（防 16h 级假死）
    - SIGTERM/SIGINT/atexit → heartbeat phase=shutdown（便于 monitor_v2 区分干净退出 vs 死进程）
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

    def _print_gates(prefix="[*]"):
        print(
            f"{prefix} Gates: ADX>={getattr(_cfg, 'ADX_STRONG_THRESHOLD', '?')} "
            f"conf>={getattr(_cfg, 'CONFIDENCE_THRESHOLD', '?')} "
            f"|DI|>={getattr(_cfg, 'MIN_DI_DIFF', '?')} "
            f"symbols={getattr(_cfg, 'TRADING_SYMBOLS', [])}"
        )

    print(f"[*] Scan interval: {interval} seconds")
    print(f"[*] Scan hard timeout: {SCAN_HARD_TIMEOUT_SEC:.0f}s | sleep heartbeat: {SLEEP_HEARTBEAT_SEC:.0f}s")
    _print_gates()
    print("[*] Starting main loop (reload only when config/paper_trader mtime changes)...\n")

    heartbeat_path = os.path.join(repo, 'logs', 'executor_heartbeat.json')
    # Carry last successful scan metrics into sleeping heartbeats (monitors
    # otherwise only see sleep_remaining and lose equity/idle/gates).
    _last_scan_hb = {}
    _shutting_down = {'done': False}

    def _write_shutdown(reason: str):
        if _shutting_down['done']:
            return
        _shutting_down['done'] = True
        extra = {'reason': str(reason)[:120]}
        for k, v in _last_scan_hb.items():
            if k not in extra:
                extra[k] = v
        # Inline write (avoid depending on nested def order before _write_heartbeat exists)
        payload = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'phase': 'shutdown',
            'pid': os.getpid(),
        }
        payload.update(extra)
        try:
            os.makedirs(os.path.dirname(heartbeat_path), exist_ok=True)
            with open(heartbeat_path, 'w', encoding='utf-8') as hf:
                import json as _json
                _json.dump(payload, hf)
            print(f"[*] Heartbeat phase=shutdown ({reason})")
        except Exception as he:
            print(f"[!] shutdown heartbeat failed: {he}")

    def _on_signal(signum, _frame):
        name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        _write_shutdown(f'signal:{name}')
        # Re-raise default so process exits (loop may be in sleep)
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    atexit.register(lambda: _write_shutdown('atexit'))
    for _sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(_sig, _on_signal)
        except Exception:
            pass

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

    def _sleep_chunked(total_sec: float):
        """Sleep in chunks; refresh heartbeat so monitors see liveness during idle."""
        remaining = float(total_sec)
        chunk = max(5.0, float(SLEEP_HEARTBEAT_SEC))
        wake_at = time.time() + remaining
        while remaining > 0:
            step = min(chunk, remaining)
            sleep_extra = {
                'sleep_remaining_sec': round(remaining, 1),
                'next_scan_eta_sec': round(max(0.0, wake_at - time.time()), 1),
                'scan_interval': float(interval),
            }
            # Preserve last scan snapshot fields for external health checks.
            for k, v in _last_scan_hb.items():
                if k not in sleep_extra:
                    sleep_extra[k] = v
            _write_heartbeat('sleeping', sleep_extra)
            time.sleep(step)
            remaining = wake_at - time.time()

    # Single worker so a timed-out scan cannot pile up threads (ccxt may still run until OS kills).
    _scan_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='scan')

    while True:
        loop_t0 = time.time()
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
                _print_gates(prefix="[*] After reload")
            _write_heartbeat('scan_start', {
                'hard_timeout_sec': SCAN_HARD_TIMEOUT_SEC,
            })
            t0 = time.time()
            fut = _scan_pool.submit(_pt.scan_and_trade_v2)
            timed_out = False
            try:
                fut.result(timeout=SCAN_HARD_TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                timed_out = True
                print(
                    f"[!] Scan hard-timeout after {SCAN_HARD_TIMEOUT_SEC:.0f}s — "
                    f"skipping rest of cycle (possible hung Binance/DNS). "
                    f"Next scan will retry; consider restarting if this repeats."
                )
                _write_heartbeat('scan_timeout', {
                    'scan_seconds': round(time.time() - t0, 2),
                    'hard_timeout_sec': SCAN_HARD_TIMEOUT_SEC,
                    'error': f'scan exceeded {SCAN_HARD_TIMEOUT_SEC:.0f}s',
                })
                # Do not wait forever on the stuck future; replace pool worker.
                try:
                    _scan_pool.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    _scan_pool.shutdown(wait=False)
                _scan_pool = concurrent.futures.ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix='scan'
                )
            dt = time.time() - t0
            if not timed_out:
                print(f"[*] Scan done in {dt:.1f}s")
                snap = getattr(_pt, 'LAST_SCAN_SNAPSHOT', None) or {}
                hb_extra = {'scan_seconds': round(dt, 2)}
                for k in (
                    'equity', 'balance', 'positions', 'actionable',
                    'max_adx', 'max_di', 'max_conf', 'ret_pct', 'quiet',
                    'fail_adx', 'fail_conf', 'fail_di',
                    'last_trade_iso', 'idle_hours_since_last_trade',
                    'idle_alert', 'idle_alert_hours',
                    'gate_adx', 'gate_conf', 'gate_di',
                ):
                    if k in snap:
                        hb_extra[k] = snap[k]
                _last_scan_hb = {
                    k: hb_extra[k] for k in hb_extra
                    if k not in ('scan_seconds',)
                }
                _last_scan_hb['last_scan_seconds'] = hb_extra.get('scan_seconds')
                _write_heartbeat('scan_done', hb_extra)
                if dt > max(60.0, float(interval) * 0.8):
                    print(f"[!] Slow scan: {dt:.1f}s (interval={interval}s)")
        except Exception as e:
            print(f"[!] Executor error: {e}")
            import traceback
            traceback.print_exc()
            _write_heartbeat('error', {'error': str(e)[:200]})

        # Wall-clock jump detection (VM pause / long hang waking into sleep)
        slept_plan = float(interval)
        pre_sleep = time.time()
        _sleep_chunked(slept_plan)
        slept_actual = time.time() - pre_sleep
        if slept_actual > slept_plan * 2.5 + 30:
            jump_h = (slept_actual - slept_plan) / 3600.0
            print(
                f"[!] Wall-clock jump during sleep: planned={slept_plan:.0f}s "
                f"actual={slept_actual:.0f}s (~{jump_h:.2f}h extra) — possible host pause"
            )
            _write_heartbeat('clock_jump', {
                'planned_sleep_sec': round(slept_plan, 1),
                'actual_sleep_sec': round(slept_actual, 1),
                'extra_hours': round(jump_h, 3),
                'loop_seconds': round(time.time() - loop_t0, 1),
            })

if __name__ == '__main__':
    main()
