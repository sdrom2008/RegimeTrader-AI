# Edge slice → paper apply (2026-09-11 CST)

## Source
- `reports/edge_slice_search.md` — last 2y 1h × 5 symbols, fee 4bps + slip 2bps
- Baseline (conf≥0.80 ADX≥25): n=1641 WR=52.6% **PF=0.79**
- Candidate (conf≥0.85 ADX≥35 |DI|≥15 both): n=173 WR=72.3% **PF=2.14** avgR=+0.31

## Applied to paper (`config.py` / `paper_trader.py`)
- `CONFIDENCE_THRESHOLD=0.85`
- `ADX_STRONG_THRESHOLD=35`
- `MIN_DI_DIFF=15.0` (gate on `| +DI - -DI |`)
- `TRAIL_ACTIVATE_R=99` (approx trail OFF; related slice favored OFF)

## Caveats
- Slice search is **not** strict walk-forward (train overlap risk).
- High-PF tiny-n slices (e.g. conf0.90 short n≈25–33) treated as overfit risk — not applied.
- Next: rerun `walk_forward_v1.py` under these gates; keep paper collecting.

## Product stance
Few high-quality shots after fees+slippage; OOS PF≥1.2 remains the real-money bar.
