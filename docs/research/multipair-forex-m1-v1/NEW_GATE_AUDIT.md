# CASIO Multi-Pair New Gate Audit

Date: 2026-09-25

## Target

- fixed RR 1:3
- WR 30-40%
- minimum 8 trades in every completed month
- PF 1.5-1.9
- RM100 start
- 5% current-equity risk reported
- real SL only
- no BE / protected stop
- causal MTF / M1 execution where applicable

## Data

- FxPro EURUSD M1
- FxPro GBPUSD M1
- FxPro GBPJPY M1
- 2017 through 2026 YTD
- 116 completed audit months through August 2026

The strict monthly frequency condition therefore requires at least 928 completed trades and >=8 in each of the 116 completed months.

## Result

Existing/transferred strategy passes: **0**.

The bounded 2,430-variant MTF deep-retracement search contains 39 variants inside the requested **30-40% WR / PF 1.5-1.9 gross** band, but the highest-trade member has only **111 trades** across the whole 2017-2026 sample, roughly 0.96/month. Therefore every quality-qualified precision candidate fails frequency by a very large margin.

### Closest frequency-qualified engine

EURUSD `FIBORSI8_23_77_HTF32.5`:
- 2,947 trades
- 30.743% WR
- fixed-3R gross PF = 1.332
- 25.22 trades/month average
- minimum 14 trades/month
- clears frequency decisively
- fails PF >=1.50

### Closest quality-qualified candidate

MTF deep retracement:
- New York window
- H1/H4 aligned
- ADX 28
- body >=0.5 ATR
- body/range >=0.72
- prior-16 break
- 70.5% retracement
- M1 confirmation
- fixed 3R

Result:
- 111 trades
- 34.234% WR
- gross PF 1.562
- ~0.96 trades/month
- minimum completed-month frequency cannot approach 8

A neighboring candidate:
- 108 trades
- 34.259% WR
- gross PF 1.563
- also far below the frequency floor

## Verdict

**No tested candidate currently satisfies all three simultaneously:**
1. WR 30-40%
2. PF 1.5-1.9
3. >=8 trades in every completed month

The research bottleneck has shifted. We no longer need a 70% WR system. We need to raise the quality of a genuinely high-frequency engine from roughly PF 1.33 to >=1.50 **without destroying frequency**.

The strongest starting point for the next iteration is EURUSD FiboRSI/high-frequency mean-reversion, because it already clears the monthly frequency floor by a wide margin. The high-PF displacement/retracement family should be treated as a quality sleeve, not a primary engine.
