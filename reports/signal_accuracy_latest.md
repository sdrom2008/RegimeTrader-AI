# Signal accuracy (observe journal)

- Generated: `2026-09-24 15:36:15` (local)
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
- Total journal rows: 9770

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

## Near-miss gate variants (last 72h, uniq bars, pred in {{0,2}})

| Gates ADX/conf/|DI| | Pass | Uniq trend bars scanned |
|---|---:|---:|
| `35/0.85/15` | 0 | 74 |
| `30/0.85/15` | 0 | 74 |
| `35/0.80/15` | 0 | 74 |
| `30/0.80/12` | 0 | 74 |

_Pass = would clear that gate set. Live paper now uses ADX≥35/conf≥0.8/|DI|≥15; other rows are research-only._

## Choke breakdown (72h uniq trend bars vs live 35/0.8/15)

- Uniq trend bars: **74**
- Ordered first-fail (ADX→conf→|DI|, matches paper scan): fail_adx=51 fail_conf=23 fail_di=0 PASS=0
- Unordered (a bar can count in multiple fail_*): fail_adx=51 fail_conf=64 fail_di=64 PASS=0 fail_any=74

| Combo | N |
|---|---:|
| `combo_adx+conf` | 4 |
| `combo_adx+conf+di` | 37 |
| `combo_adx+di` | 10 |
| `combo_conf` | 6 |
| `combo_conf+di` | 17 |

## Pass counts by recent window (uniq trend bars)

| Gates | 6h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| `35/0.85/15` | 0 | 0 | 0 | 0 |
| `30/0.85/15` | 0 | 0 | 0 | 0 |
| `35/0.80/15` | 0 | 0 | 0 | 0 |
| `30/0.80/12` | 0 | 0 | 0 | 0 |

