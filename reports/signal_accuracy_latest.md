# Signal accuracy (observe journal)

- Generated: `2026-09-18 07:07:52` (local)
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
- Total journal rows: 6106

_No matured actionable signals yet. Re-run after ≥24h of observe logging._

## Near-miss gate variants (last 72h, uniq bars, pred in {{0,2}})

| Gates ADX/conf/|DI| | Pass | Uniq trend bars scanned |
|---|---:|---:|
| `35/0.85/15` | 0 | 163 |
| `30/0.85/15` | 0 | 163 |
| `35/0.80/15` | 1 | 163 |
| `30/0.80/12` | 9 | 163 |

_Pass = would clear that gate set. Live paper now uses ADX≥35/conf≥0.8/|DI|≥15; other rows are research-only._

## Choke breakdown (72h uniq trend bars vs live 35/0.8/15)

- Uniq trend bars: **163**
- Ordered first-fail (ADX→conf→|DI|, matches paper scan): fail_adx=91 fail_conf=48 fail_di=23 PASS=1
- Unordered (a bar can count in multiple fail_*): fail_adx=91 fail_conf=106 fail_di=126 PASS=1 fail_any=162

| Combo | N |
|---|---:|
| `PASS` | 1 |
| `combo_adx` | 2 |
| `combo_adx+conf` | 17 |
| `combo_adx+conf+di` | 41 |
| `combo_adx+di` | 31 |
| `combo_conf` | 17 |
| `combo_conf+di` | 31 |
| `combo_di` | 23 |

## Pass counts by recent window (uniq trend bars)

| Gates | 6h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| `35/0.85/15` | 0 | 0 | 0 | 0 |
| `30/0.85/15` | 0 | 0 | 0 | 0 |
| `35/0.80/15` | 0 | 0 | 0 | 1 |
| `30/0.80/12` | 0 | 2 | 3 | 9 |

