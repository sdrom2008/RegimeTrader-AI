# Signal accuracy (observe journal)

- Generated: `2026-09-12 07:14:52` (local)
- Journal: `logs/signal_journal.jsonl`
- Horizon: `24` × 1h bars
- Gates: ADX>=35, conf>=0.85, DI agrees
- Rule: BUY hit if close_fwd>close; SELL hit if close_fwd<close

## Hit rate by direction

| Direction | Hits | N | Hit rate |
|---|---:|---:|---:|
| BUY | 3 | 3 | 100.0% |
| SELL | 0 | 0 | 0.0% |
| **ALL** | 3 | 3 | **100.0%** |

- Pending (too young / missing fwd): 17
- Actionable journal rows (deduped): 20
- Actionable raw (pre-dedupe): 88
- Total journal rows: 2062

## Evaluated signals

| Time (UTC) | Symbol | Dir | Close | Fwd | Ret% | Hit | Conf |
|---|---|---|---:|---:|---:|:---:|---:|
| 2026-09-10T17:37:58 | BNB/USDT | BUY | 712.5000 | 722.3800 | +1.39 | Y | 0.904 |
| 2026-09-10T17:53:15 | ETH/USDT | BUY | 2470.0000 | 2537.3000 | +2.72 | Y | 0.850 |
| 2026-09-11T04:27:52 | BNB/USDT | BUY | 715.7200 | 732.9400 | +2.41 | Y | 0.888 |

