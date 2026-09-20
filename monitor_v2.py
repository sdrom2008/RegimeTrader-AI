#!/usr/bin/env python3
"""Paper executor health via logs/executor_heartbeat.json.

Usage:
  python monitor_v2.py              # human summary, exit 0/1/2
  python monitor_v2.py --json       # machine-readable
  python monitor_v2.py --write      # also write logs/executor_health.json

Exit codes: 0=ok, 1=stale/dead, 2=missing heartbeat.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
HB_PATH = os.path.join(REPO, "logs", "executor_heartbeat.json")
OUT_PATH = os.path.join(REPO, "logs", "executor_health.json")
# Fresh if heartbeat younger than this (scan interval 300s + sleep chunks + slack).
DEFAULT_STALE_SEC = float(os.environ.get("EXECUTOR_STALE_SEC", "900"))  # 15 min


def _parse_ts(s: str) -> dt.datetime:
    s = str(s).replace("Z", "+00:00")
    if s.endswith("+00:00") or (len(s) > 6 and (s[-6] in "+-" or s.endswith("Z"))):
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    naive = dt.datetime.fromisoformat(s)
    return naive.replace(tzinfo=dt.timezone.utc)


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def check(stale_sec: float = DEFAULT_STALE_SEC) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    result = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "heartbeat_path": HB_PATH,
        "status": "missing",
        "stale_sec_threshold": stale_sec,
        "age_sec": None,
        "pid": None,
        "pid_alive": False,
        "phase": None,
        "equity": None,
        "idle_hours_since_last_trade": None,
        "idle_alert": None,
        "fail_adx": None,
        "fail_conf": None,
        "fail_di": None,
        "max_adx": None,
        "max_di": None,
        "max_conf": None,
        "last_hb_ts": None,
        "message": "",
    }
    if not os.path.exists(HB_PATH):
        result["message"] = "heartbeat file missing — executor never started or logs wiped"
        result["status"] = "missing"
        return result

    try:
        with open(HB_PATH, "r", encoding="utf-8") as f:
            hb = json.load(f)
    except Exception as e:
        result["status"] = "missing"
        result["message"] = f"heartbeat unreadable: {e}"
        return result

    result["last_hb_ts"] = hb.get("ts")
    result["pid"] = hb.get("pid")
    result["phase"] = hb.get("phase")
    result["pid_alive"] = _pid_alive(hb.get("pid"))
    for k in (
        "equity",
        "idle_hours_since_last_trade",
        "idle_alert",
        "fail_adx",
        "fail_conf",
        "fail_di",
        "max_adx",
        "max_di",
        "max_conf",
        "ret_pct",
        "positions",
        "actionable",
        "gate_adx",
        "gate_conf",
        "gate_di",
    ):
        if k in hb:
            result[k] = hb[k]

    try:
        hb_ts = _parse_ts(hb["ts"])
        age = (now - hb_ts).total_seconds()
        result["age_sec"] = round(age, 1)
    except Exception as e:
        result["status"] = "missing"
        result["message"] = f"bad heartbeat ts: {e}"
        return result

    phase = str(hb.get("phase") or "")
    if phase in ("stopped", "shutdown", "signal_exit"):
        result["status"] = "stopped"
        result["message"] = (
            f"executor cleanly stopped (phase={phase}, age={age/3600:.1f}h, "
            f"pid_alive={result['pid_alive']})"
        )
        return result

    if age > stale_sec or not result["pid_alive"]:
        result["status"] = "dead"
        why = []
        if age > stale_sec:
            why.append(f"heartbeat stale {age/3600:.1f}h (>{stale_sec:.0f}s)")
        if not result["pid_alive"]:
            why.append(f"pid {hb.get('pid')} not alive")
        result["message"] = "executor DEAD: " + "; ".join(why)
        return result

    result["status"] = "ok"
    result["message"] = (
        f"ok phase={phase} age={age:.0f}s equity={hb.get('equity')} "
        f"idle_h={hb.get('idle_hours_since_last_trade')} "
        f"fail_adx={hb.get('fail_adx')}"
    )
    return result


def _restart_dry_bg(reason: str) -> int:
    """Stop any live_executor and start DRY_RUN via start.sh (low-risk recovery)."""
    start_sh = os.path.join(REPO, "start.sh")
    if not os.path.isfile(start_sh):
        print(f"restart aborted: missing {start_sh}", file=sys.stderr)
        return 2
    import subprocess

    print(f"watchdog restart: {reason}")
    # stop (ignore non-zero)
    subprocess.run(["bash", start_sh, "stop"], cwd=REPO, check=False)
    # brief wait so port/pidfile clears
    import time as _time

    _time.sleep(1.5)
    r = subprocess.run(["bash", start_sh, "dry", "bg"], cwd=REPO, check=False)
    return 0 if r.returncode == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="RegimeTrader executor heartbeat monitor")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    ap.add_argument("--write", action="store_true", help="write logs/executor_health.json")
    ap.add_argument(
        "--stale-sec",
        type=float,
        default=DEFAULT_STALE_SEC,
        help="stale threshold seconds (default 900)",
    )
    ap.add_argument(
        "--restart-if-dead",
        action="store_true",
        help="if status=dead/missing, stop + ./start.sh dry bg (for cron/watchdog)",
    )
    ap.add_argument(
        "--force-restart-age-sec",
        type=float,
        default=float(os.environ.get("EXECUTOR_FORCE_RESTART_SEC", "7200")),
        help="when pid alive but HB stale this long, still restart (default 2h)",
    )
    args = ap.parse_args()
    result = check(stale_sec=args.stale_sec)

    if args.write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"status={result['status']}")
        print(result["message"])
        if result.get("last_hb_ts"):
            print(
                f"last_hb={result['last_hb_ts']} age_sec={result['age_sec']} "
                f"pid={result['pid']} alive={result['pid_alive']} phase={result['phase']}"
            )
        if result.get("equity") is not None:
            print(
                f"equity={result.get('equity')} idle_h={result.get('idle_hours_since_last_trade')} "
                f"fail_adx/conf/di={result.get('fail_adx')}/{result.get('fail_conf')}/{result.get('fail_di')} "
                f"near max_adx/di/conf={result.get('max_adx')}/{result.get('max_di')}/{result.get('max_conf')}"
            )

    code = {"ok": 0, "stopped": 1, "dead": 1, "missing": 2}.get(result["status"], 2)

    if args.restart_if_dead:
        age = result.get("age_sec")
        status = result.get("status")
        pid_alive = bool(result.get("pid_alive"))
        # Restart when: missing, or dead with pid gone, or zombie (alive+stale >= force age).
        # Skip clean stopped (manual stop / shutdown phase) unless missing pid forever.
        do_restart = False
        reason = ""
        if status == "missing":
            do_restart = True
            reason = "heartbeat missing"
        elif status == "dead":
            if not pid_alive:
                do_restart = True
                reason = result.get("message") or "dead (pid gone)"
            elif age is not None and float(age) >= float(args.force_restart_age_sec):
                do_restart = True
                reason = (
                    f"zombie: pid alive but HB stale {float(age)/3600:.1f}h "
                    f"(>={args.force_restart_age_sec:.0f}s)"
                )
            else:
                # alive+stale but under force age — likely host pause; wait for wake or force age
                print(
                    f"watchdog defer: pid alive, HB stale {float(age or 0)/3600:.1f}h "
                    f"< force {args.force_restart_age_sec:.0f}s (possible host pause)"
                )
        if do_restart:
            rc = _restart_dry_bg(reason)
            sys.exit(rc)

    sys.exit(code)


if __name__ == "__main__":
    main()
