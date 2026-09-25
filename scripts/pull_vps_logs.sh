#!/bin/bash
# Pull RegimeTrader-AI DRY_RUN scan logs/state from the VPS (systemd: regimetrader.service,
# /opt/regimetrader/app) back into this repo so the daily report keeps working.
#
# Bandwidth-friendly (VPS uplink 3 Mbps, shared with the VPN):
#   - rsync -z --bwlimit (KB/s), append-only files use --append-verify (only new bytes cross)
#   - only small files: journal, trader logs, heartbeat/health, paper state
# Merge rules (box side, idempotent):
#   - logs/signal_journal.jsonl  += new VPS journal lines   (export_gate_rejects_daily reads this)
#   - logs/v2_trader.log / logs/paper_sim_keep.log += new VPS bytes (rotation/truncation safe)
#   - paper_trade_state_v2.json  <- VPS copy (only when no local live_executor is running)
#   - VPS heartbeat/health go to logs/vps/ ONLY (never overwrite local heartbeat:
#     the local watchdog would treat the remote pid as dead and restart a 2nd copy)
#
# Usage:  scripts/pull_vps_logs.sh            (then run the normal daily report)
# Env:    RT_VPS_HOST (default 47.243.62.86)  RT_VPS_KEY (default ~/.ssh/id_ed25519_rt_vps)
#         RT_VPS_BWLIMIT KB/s (default 150)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
HOST="${RT_VPS_HOST:-47.243.62.86}"
KEY="${RT_VPS_KEY:-$HOME/.ssh/id_ed25519_rt_vps}"
BW="${RT_VPS_BWLIMIT:-150}"
REMOTE="/opt/regimetrader/app"
DEST="$ROOT/logs/vps"
mkdir -p "$DEST"

SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new"
RSYNC=(rsync -z --bwlimit="$BW" --timeout=120 -e "$SSH")

# 1) append-only files: transfer only new bytes (falls back to full copy if verify fails)
"${RSYNC[@]}" --append-verify \
  "root@$HOST:$REMOTE/logs/signal_journal.jsonl" \
  "root@$HOST:$REMOTE/logs/paper_sim_keep.log" \
  "$DEST/"
# 2) rotating / small files: normal rsync delta
"${RSYNC[@]}" \
  "root@$HOST:$REMOTE/logs/v2_trader.log" \
  "root@$HOST:$REMOTE/logs/executor_heartbeat.json" \
  "root@$HOST:$REMOTE/logs/executor_health.json" \
  "root@$HOST:$REMOTE/paper_trade_state_v2.json" \
  "$DEST/"

# 3) merge into the paths the daily report / export script already read
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3
"$PY" - "$ROOT" <<'PYEOF'
import json, os, sys
root = sys.argv[1]
vps = os.path.join(root, 'logs', 'vps')
offp = os.path.join(vps, '.merge_offsets.json')
try:
    offs = json.load(open(offp))
except Exception:
    offs = {}

def merge(src_name, dst_rel, whole_lines=True):
    src = os.path.join(vps, src_name)
    dst = os.path.join(root, dst_rel)
    if not os.path.exists(src):
        return 0
    size = os.path.getsize(src)
    off = int(offs.get(src_name, 0))
    if size < off:          # VPS file rotated/truncated -> start over from 0
        off = 0
    with open(src, 'rb') as f:
        f.seek(off)
        data = f.read()
    if whole_lines:         # never merge a half-written trailing line
        cut = data.rfind(b'\n') + 1
        data = data[:cut]
    if data:
        with open(dst, 'ab') as g:
            g.write(data)
    offs[src_name] = off + len(data)
    return len(data)

n1 = merge('signal_journal.jsonl', 'logs/signal_journal.jsonl')
n2 = merge('v2_trader.log', 'logs/v2_trader.log')
n3 = merge('paper_sim_keep.log', 'logs/paper_sim_keep.log')
json.dump(offs, open(offp + '.tmp', 'w'), indent=1)
os.replace(offp + '.tmp', offp)
print(f"merged bytes: journal={n1} v2_trader={n2} paper_sim_keep={n3}")
try:
    hb = json.load(open(os.path.join(vps, 'executor_heartbeat.json')))
    print(f"VPS heartbeat: ts={hb.get('ts')} phase={hb.get('phase')} equity={hb.get('equity')} "
          f"gates=ADX{hb.get('gate_adx')}/conf{hb.get('gate_conf')}/DI{hb.get('gate_di')}")
except Exception as e:
    print(f"VPS heartbeat unreadable: {e}")
PYEOF

# 4) paper state continuity (skip if a local executor is somehow running)
if pgrep -f "[l]ive_executor.py" >/dev/null 2>&1; then
  echo "WARN: local live_executor.py is running -> not overwriting paper_trade_state_v2.json (only one instance should run; VPS is primary)"
else
  cp -f "$DEST/paper_trade_state_v2.json" "$ROOT/paper_trade_state_v2.json"
fi
touch "$ROOT/logs/EXECUTOR_ON_VPS"
echo "pull_vps_logs: OK $(date '+%F %T %Z')"
