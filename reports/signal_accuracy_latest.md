# Signal accuracy (observe journal)

- Generated: `2026-09-14 07:13:14` (local)
- Journal: `logs/signal_journal.jsonl`
- Horizon: `24` × 1h bars
- Gates (re-applied): ADX>=35, conf>=0.85, |DI|>=15.0, whitelist=['ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
- Note: ignores historical `gates_passed` under looser thresholds (legacy raw=88)
- Rule: BUY hit if close_fwd>close; SELL hit if close_fwd<close

## Hit rate by direction

| Direction | Hits | N | Hit rate |
|---|---:|---:|---:|
| BUY | 0 | 0 | 0.0% |
| SELL | 0 | 0 | 0.0% |
| **ALL** | 0 | 0 | **0.0%** |

- Pending (too young / missing fwd): 0
- Actionable journal rows (deduped): 0
- Actionable raw (pre-dedupe): 0
- Total journal rows: 2878

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

## Near-miss gate variants (last 72h, uniq bars, pred in {{0,2}})

| Gates ADX/conf/|DI| | Pass | Uniq trend bars scanned |
|---|---:|---:|
| `35/0.85/15` | 0 | 82 |
| `30/0.85/15` | 0 | 82 |
| `35/0.80/15` | 0 | 82 |
| `30/0.80/12` | 2 | 82 |

_Pass = would clear that gate set. Live paper still uses config thresholds; this table is research-only._

