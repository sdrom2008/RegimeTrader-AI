#!/bin/bash
# RegimeTrader AI 快速启动脚本
# 用法:
#   ./start.sh              # dry, foreground
#   ./start.sh dry          # dry, foreground
#   ./start.sh dry bg       # dry, background (nohup → logs/paper_sim_keep.log)
#   ./start.sh live         # live, foreground (interactive confirm)
#   ./start.sh status       # heartbeat health via monitor_v2.py
#   ./start.sh stop         # stop DRY_RUN live_executor by pidfile / pgrep
#   ./start.sh watchdog     # restart dry bg if dead/missing/zombie HB
#   ./start.sh install-cron # write cron example + try crontab install (*/15)
#   ./start.sh cron-check   # report crontab presence + last watchdog_events line

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODE="${1:-dry}"
BG="${2:-}"

# Prefer local .venv, then venv, then python3
if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
    PYTHON="$ROOT/venv/bin/python"
else
    PYTHON="python3"
fi

mkdir -p logs scripts
PIDFILE="$ROOT/logs/executor.pid"
LOGFILE="$ROOT/logs/paper_sim_keep.log"
CRON_EXAMPLE="$ROOT/scripts/watchdog.cron.example"

_already_running() {
    # Prefer pidfile; fall back to pgrep on live_executor.py
    if [ -f "$PIDFILE" ]; then
        oldpid="$(cat "$PIDFILE" 2>/dev/null || true)"
        if [ -n "$oldpid" ] && kill -0 "$oldpid" 2>/dev/null; then
            echo "$oldpid"
            return 0
        fi
    fi
    found="$(pgrep -f "[l]ive_executor.py" 2>/dev/null | head -1 || true)"
    if [ -n "$found" ] && kill -0 "$found" 2>/dev/null; then
        echo "$found"
        return 0
    fi
    return 1
}

# --- ops commands MUST run even when executor is already up ---
if [ "$MODE" = "status" ]; then
    "$PYTHON" monitor_v2.py --write
    exit $?
fi

if [ "$MODE" = "stop" ]; then
    stopped=0
    if [ -f "$PIDFILE" ]; then
        old="$(cat "$PIDFILE" 2>/dev/null || true)"
        if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
            kill "$old" && echo "✅ Sent SIGTERM to PID $old"
            stopped=1
        fi
        rm -f "$PIDFILE"
    fi
    # Also match dry-run executors started without pidfile
    if pgrep -f "live_executor.py" >/dev/null 2>&1; then
        pkill -f "live_executor.py" && echo "✅ pkill live_executor.py" && stopped=1 || true
    fi
    if [ "$stopped" = "0" ]; then
        echo "ℹ️ No live_executor process found"
    fi
    exit 0
fi

if [ "$MODE" = "watchdog" ]; then
    # Cron-friendly: restart DRY_RUN if heartbeat missing/dead or zombie (>2h stale).
    # Does NOT touch live gates. Safe to run every 10–15 min.
    # CRITICAL: must NOT go through the duplicate-start guard below.
    exec "$PYTHON" monitor_v2.py --write --restart-if-dead
fi

if [ "$MODE" = "install-cron" ]; then
    # Write portable crontab snippet; install if `crontab` exists.
    cat > "$CRON_EXAMPLE" <<EOF
# RegimeTrader-AI paper DRY_RUN watchdog — every 15 minutes
*/15 * * * * cd $ROOT && ./start.sh watchdog >>$ROOT/logs/watchdog_cron.log 2>&1
EOF
    echo "✅ Wrote $CRON_EXAMPLE"
    if command -v crontab >/dev/null 2>&1; then
        tmp="$(mktemp)"
        crontab -l 2>/dev/null | grep -v 'RegimeTrader-AI paper DRY_RUN watchdog' | grep -v "$ROOT/start.sh watchdog" >"$tmp" || true
        cat "$CRON_EXAMPLE" >>"$tmp"
        crontab "$tmp"
        rm -f "$tmp"
        echo "✅ Installed into user crontab (*/15 ./start.sh watchdog)"
        crontab -l | tail -n 5
    else
        echo "⚠️ crontab binary not found on this host — copy $CRON_EXAMPLE to the host that runs the box/VM."
        echo "   Example line:"
        cat "$CRON_EXAMPLE"
    fi
    # Ensure durable event log exists even before first watchdog fire
    mkdir -p logs
    touch logs/watchdog_events.log
    exit 0
fi

if [ "$MODE" = "cron-check" ]; then
    echo "=== RegimeTrader cron / watchdog observability ==="
    if command -v crontab >/dev/null 2>&1; then
        echo "crontab_binary=yes"
        echo "--- crontab -l (watchdog lines) ---"
        crontab -l 2>/dev/null | grep -E 'watchdog|RegimeTrader' || echo "(no RegimeTrader watchdog lines in crontab)"
    else
        echo "crontab_binary=NO — host/VM must install cron; box alone cannot auto-recover from long pauses"
        echo "  fix: on the awake host run: cd $ROOT && ./start.sh install-cron"
    fi
    if [ -f "$CRON_EXAMPLE" ]; then
        echo "--- $CRON_EXAMPLE ---"
        cat "$CRON_EXAMPLE"
    else
        echo "missing $CRON_EXAMPLE (run ./start.sh install-cron to write it)"
    fi
    ev="$ROOT/logs/watchdog_events.log"
    if [ -f "$ev" ] && [ -s "$ev" ]; then
        echo "--- last 5 watchdog_events ---"
        tail -n 5 "$ev"
    else
        echo "watchdog_events: empty/missing ($ev) — no defer/restart recorded yet"
    fi
    exit 0
fi

# Refuse duplicate start (dry/live only)
if existing="$(_already_running)"; then
    if [ -n "$existing" ] && kill -0 "$existing" 2>/dev/null; then
        echo "⚠️ live_executor already running (PID $existing). Use: ./start.sh status|stop|watchdog"
        exit 1
    fi
fi

if [ "$MODE" = "dry" ]; then
    echo "🧪 启动模拟盘（DRY_RUN=1）... python=$PYTHON"
    if [ "$BG" = "bg" ] || [ "$BG" = "background" ] || [ "$BG" = "-d" ]; then
        # Stale heartbeat note (non-fatal)
        "$PYTHON" monitor_v2.py --write >/dev/null 2>&1 || true
        nohup env DRY_RUN=1 "$PYTHON" -u live_executor.py >> "$LOGFILE" 2>&1 &
        echo $! > "$PIDFILE"
        echo "✅ DRY_RUN live_executor started PID=$(cat "$PIDFILE") log=$LOGFILE"
        echo "   status: ./start.sh status"
        exit 0
    fi
    DRY_RUN=1 exec "$PYTHON" -u live_executor.py
elif [ "$MODE" = "live" ]; then
    echo "🔥 启动实盘（DRY_RUN=0）... 注意：将执行真实订单！"
    read -p "确认已小资金测试且理解风险？(yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        DRY_RUN=0 exec "$PYTHON" -u live_executor.py
    else
        echo "取消启动"
        exit 1
    fi
else
    echo "用法: $0 [dry|live|status|stop|watchdog|install-cron|cron-check] [bg]"
    echo "  dry          - 模拟盘前台（默认）"
    echo "  dry bg       - 模拟盘后台（推荐常驻）"
    echo "  live         - 实盘前台（需确认）"
    echo "  status       - 读 heartbeat / 写 executor_health.json"
    echo "  stop         - 停止 live_executor"
    echo "  watchdog     - 若 dead/missing/僵尸则 stop + dry bg（建议 cron）"
    echo "  install-cron - 写入 scripts/watchdog.cron.example；有 crontab 则安装 */15"
    echo "  cron-check   - 检查 crontab 是否存在 + 最近 watchdog_events"
    exit 1
fi
