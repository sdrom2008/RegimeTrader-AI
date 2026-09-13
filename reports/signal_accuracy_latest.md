# Signal accuracy (observe journal)

- Generated: `2026-09-13 07:25:24` (local)
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
- Total journal rows: 2178

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

