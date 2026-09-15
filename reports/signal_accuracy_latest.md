# Signal accuracy (observe journal)

- Generated: `2026-09-15 07:18:17` (local)
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
- Total journal rows: 3770

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

## Near-miss gate variants (last 72h, uniq bars, pred in {{0,2}})

| Gates ADX/conf/|DI| | Pass | Uniq trend bars scanned |
|---|---:|---:|
| `35/0.85/15` | 0 | 48 |
| `30/0.85/15` | 0 | 48 |
| `35/0.80/15` | 4 | 48 |
| `30/0.80/12` | 6 | 48 |

_Pass = would clear that gate set. Live paper still uses config thresholds; this table is research-only._

## Choke breakdown (72h uniq trend bars vs live 35/0.85/15)

- Uniq trend bars: **48**
- fail_adx=31 fail_conf=46 fail_di=32 PASS=0 fail_any=48

| Combo | N |
|---|---:|
| `combo_adx+conf` | 5 |
| `combo_adx+conf+di` | 25 |
| `combo_adx+di` | 1 |
| `combo_conf` | 11 |
| `combo_conf+di` | 5 |
| `combo_di` | 1 |

## Pass counts by recent window (uniq trend bars)

| Gates | 6h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| `35/0.85/15` | 0 | 0 | 0 | 0 |
| `30/0.85/15` | 0 | 0 | 0 | 0 |
| `35/0.80/15` | 4 | 4 | 4 | 4 |
| `30/0.80/12` | 4 | 4 | 4 | 6 |

