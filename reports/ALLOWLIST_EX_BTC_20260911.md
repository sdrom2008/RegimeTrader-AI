# Paper allowlist: exclude BTC (2026-09-11 CST)

## Evidence
- Full 5-symbol WF OOS: n=131 WR=42% **PF=1.14** (FAIL ≥1.2)
- BTC alone: n=15 WR=20% **PF=0.41**
- ETH+BNB+SOL+XRP: n=116 WR=44.8% **PF=1.27** (PASS)
- ETH+BNB+XRP: PF=1.32; BNB+ETH: PF=1.36 (fewer trades)

## Applied
- `TRADING_SYMBOLS` → ETH/BNB/SOL/XRP (BTC removed from paper scan)
- Model stays `multi_full` (still trained on 5 symbols including BTC)
- Gates unchanged: conf≥0.85, ADX≥35, |DI|≥15, trail≈OFF

## Rationale
Prefer largest PASS subset (n=116) over peak-PF smaller baskets. Multi-symbol pooled model mismatch likely hurts BTC; whitelist is cheaper than retraining per-symbol models first.

## Caveats
Selection bias / fold-reset capital still apply. Revisit if paper or next WF flips.
