# Signal accuracy (observe journal)

- Generated: `2026-09-16 07:14:27` (local)
- Journal: `logs/signal_journal.jsonl`
- Horizon: `24` × 1h bars
- Gates (re-applied): ADX>=35, conf>=0.8, |DI|>=15.0, whitelist=['ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
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
- Total journal rows: 4838

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

## Near-miss gate variants (last 72h, uniq bars, pred in {{0,2}})

| Gates ADX/conf/|DI| | Pass | Uniq trend bars scanned |
|---|---:|---:|
| `35/0.85/15` | 0 | 121 |
| `30/0.85/15` | 0 | 121 |
| `35/0.80/15` | 4 | 121 |
| `30/0.80/12` | 9 | 121 |

_Pass = would clear that gate set. Live paper now uses ADX≥35/conf≥0.8/|DI|≥15; other rows are research-only._

## Choke breakdown (72h uniq trend bars vs live 35/0.8/15)

- Uniq trend bars: **121**
- Ordered first-fail (ADX→conf→|DI|, matches paper scan): fail_adx=53 fail_conf=43 fail_di=21 PASS=4
- Unordered (a bar can count in multiple fail_*): fail_adx=53 fail_conf=80 fail_di=94 PASS=4 fail_any=117

| Combo | N |
|---|---:|
| `PASS` | 4 |
| `combo_adx` | 2 |
| `combo_adx+conf` | 4 |
| `combo_adx+conf+di` | 33 |
| `combo_adx+di` | 14 |
| `combo_conf` | 17 |
| `combo_conf+di` | 26 |
| `combo_di` | 21 |

## Pass counts by recent window (uniq trend bars)

| Gates | 6h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| `35/0.85/15` | 0 | 0 | 0 | 0 |
| `30/0.85/15` | 0 | 0 | 0 | 0 |
| `35/0.80/15` | 0 | 0 | 1 | 4 |
| `30/0.80/12` | 0 | 1 | 4 | 9 |

