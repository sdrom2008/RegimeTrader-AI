# Gate candidate — conf→0.80 (research only)

- Date: 2026-09-15
- Status: **NOT applied to live** (`config.py` still conf≥0.85 / ADX≥35 / |DI|≥15)
- Why candidate: paper journal choke is conf; ETH 24h bars clear ADX+DI with conf≈0.83–0.85

## Evidence

### Paper journal (72h uniq trend bars=48)

| Gates | 6h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| 35/0.85/15 (live) | 0 | 0 | 0 | 0 |
| 35/0.80/15 | 4 | 4 | 4 | 4 |

Choke vs live: fail_conf=46, fail_adx=31, fail_di=32, PASS=0.

### Offline 1y contrast with |DI|≥15 (`reports/gate_contrast_20260915.md`)

| Variant | Trades | Agg PF | Sum PnL |
|---|---:|---:|---:|
| 35/0.85/15 | 77 | 3.12 | +$12.7k |
| 30/0.85/15 | 107 | 2.56 | +$14.2k |
| **35/0.80/15** | **119** | **2.92** | **+$19.7k** |
| 30/0.80/15 | 172 | 2.25 | +$22.9k |

Relative: conf→0.80 keeps PF better than ADX-only loosen. Still train-overlap → not WF OOS proof.

## Promote criteria (next)

1. Run `walk_forward_v1.py` (or equivalent) with paper gates |DI|≥15 comparing conf 0.85 vs 0.80 (±ADX35).
2. Require OOS aggregate PF≥~1.2 and no fold blow-up before touching live `CONFIDENCE_THRESHOLD`.
3. If promoted: change only conf 0.85→0.80; keep ADX35 and |DI|15.
