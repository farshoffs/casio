# RR10 Adaptive TP / SL Research — Entry Router Frozen

## Scope

This research keeps the **canonical RR10 MTF entry/router unchanged**.

Unchanged:
- M15 0591 impulse -> pullback -> confirmation trigger
- completed H1 / H4 context
- RR10 TREND / MIXED routing
- support memory window = 2 bars
- H4 ADX strong-trend threshold = 18
- primary-session exclusion
- at least one H1/H4 alignment
- one active trade at a time
- confirmed M15-close entry
- stop-first treatment if SL and TP collide on one bar

Only the **post-entry exit policy** was researched.

Data:
- File: `fxpro_xauusd_m15.csv`
- SHA-256: `6df834d88f3fadefa19f58e75e7cb4c806db97e8fbac9ecbcc7145d18134c7cb`
- Rows: **64,190**
- Coverage: **2024-01-01 23:00 UTC -> 2026-09-18 13:30 UTC**
- Symbol / timeframe: **XAUUSD M15**
- Start equity: **RM100**
- Risk: **5% of current equity per closed trade**

Research design:
- **2024 + 2025 = development sample**
- **2026 YTD = out-of-sample check**
- 156 causal exit-policy combinations tested
- no future information used to select SL or TP

## Baseline checksum

The replay reproduces the existing RR10 fixed-target checksums.

2026 YTD:
- 2R: 79 closed trades, 51.90% WR, +0.557R expectancy, PF 2.16, RM708.92, max DD 18.55%
- 3R: 69 closed trades, 43.48% WR, +0.739R expectancy, PF 2.31, RM895.69, max DD 22.62%
- 4R: 66 closed trades, 37.88% WR, +0.894R expectancy, PF 2.44, RM1,164.66, max DD 26.49%
- 5R: 66 closed trades, 33.33% WR, +1.000R expectancy, PF 2.50, RM1,418.60, max DD 32.45%

The currently open 2026-09-17 RR10 LONG remains the same canonical entry:
- Entry: 4354.68
- current structural SL: 4323.28
- fixed 3R TP: 4448.89

## Exit families researched

### Adaptive SL

The canonical RR10 stop is already structural:
- long: 0591 pullback extreme minus an impulse-ATR buffer
- short: 0591 pullback extreme plus an impulse-ATR buffer

Research therefore did **not** move the stop inside the confirmed pullback structure.

Only the ATR buffer outside the structure was varied causally using entry quality:
- H1/H4 alignment
- TREND / MIXED regime
- H4 ADX
- confirmation support count

The base RR10 buffer is 0.12 × impulse ATR.

Tested adaptive buffers included quality maps from approximately **0.08 to 0.36 × impulse ATR**.

### Adaptive TP

Targets remained inside the requested **2R–5R range**.

Target selection used combinations of:
- H1/H4 alignment
- TREND / MIXED mode
- H4 ADX
- confirmation support
- causal structural room above/below entry from completed M15/H1/H4 and prior-day levels

No future swing or future candle was used.

## Main finding

The research does **not** justify replacing RR10's entry/router.

It also does not show that a complicated adaptive SL is automatically better than the existing structural stop. The existing 0591 stop is already a strong adaptive mechanism.

The most useful result is a **higher-hit-rate exit candidate** that preserves the router and keeps frequency close to the requested eight trades per month.

### Adaptive Candidate C1

SL rule:
- keep the same 0591 pullback extreme
- vary only the outside ATR buffer according to entry quality
- quality score 0 -> 4 uses buffer multipliers:
  **0.08, 0.10, 0.12, 0.16, 0.20 × impulse ATR**
- higher-quality / stronger entries receive more structural breathing room
- lower-quality entries are cut more tightly
- the stop always remains beyond the confirmed pullback extreme

TP rule:
1. create a causal entry-quality target:
   - quality 0 -> 2R
   - quality 1 -> 3R
   - quality 2 -> 3R
   - quality 3 -> 4R
   - quality 4 -> 5R
2. cap that target at the nearest completed structural resistance/support that offers at least 2R
3. never use less than 2R or more than 5R

In practice the structural cap is conservative: most trades select 2R.

Target distribution:
- 2024: 82 × 2R, 5 × 3R, 1 × 4R
- 2025: 101 × 2R, 4 × 3R
- 2026 YTD: 73 × 2R, 3 × 3R, 2 × 4R

## Annual comparison

| Policy | Year | Trades | Win rate | Expectancy | PF | Trades / 30d | RM100 -> | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed 2R | 2024 | 88 | 35.23% | +0.057R | 1.09 | 7.21 | RM103.14 | 39.23% |
| Fixed 2R | 2025 | 107 | 51.40% | +0.542R | 2.12 | 8.79 | RM1,312.88 | 27.55% |
| Fixed 2R | 2026 YTD | 79 | 51.90% | +0.557R | 2.16 | 9.10 | RM708.92 | 18.55% |
| Current fixed 3R | 2024 | 77 | 35.06% | +0.403R | 1.62 | 6.31 | RM334.98 | 35.50% |
| Current fixed 3R | 2025 | 95 | 44.21% | +0.768R | 2.38 | 7.81 | RM2,337.01 | 27.52% |
| Current fixed 3R | 2026 YTD | 69 | 43.48% | +0.739R | 2.31 | 7.94 | RM895.69 | 22.62% |
| **Adaptive C1** | **2024** | **88** | **35.23%** | **+0.091R** | **1.14** | **7.21** | **RM117.85** | **39.67%** |
| **Adaptive C1** | **2025** | **105** | **50.48%** | **+0.543R** | **2.10** | **8.63** | **RM1,239.81** | **24.29%** |
| **Adaptive C1** | **2026 YTD** | **78** | **52.56%** | **+0.615R** | **2.30** | **8.98** | **RM851.07** | **18.55%** |

## Interpretation

Adaptive C1 does what the research was intended to test:

- it leaves the RR10 MTF entry/router untouched
- it raises the hit rate materially versus the current fixed 3R in 2025 and 2026
- it keeps trade frequency close to ~8/month
- it retains positive expectancy in all three observed calendar periods
- its 2025 and 2026 drawdowns are lower than fixed 3R

However, it does **not** dominate current fixed 3R on expectancy:
- 2024: +0.091R vs +0.403R
- 2025: +0.543R vs +0.768R
- 2026 YTD: +0.615R vs +0.739R

And its 2024 drawdown is worse:
- Adaptive C1: 39.67%
- current fixed 3R: 35.50%

So the adaptive exit improves the user's preferred **hit-rate / frequency profile**, but it pays for that improvement by taking many 2R targets and giving up part of the fixed-3R expectancy.

## Adaptive-SL conclusion

The adaptive SL tests did **not** produce a robust reason to replace the current structural 0591 stop.

The main structural stop should remain:
- pullback extreme
- plus/minus an impulse-ATR safety buffer

The only SL adaptation worth continuing to research is the **small external ATR buffer**, not moving the stop inside the pullback structure.

Several more aggressive weak-regime widening rules produced very strong 2026 numbers (up to roughly 55–56% WR), but they were not superior in the 2024–2025 development sample. They are therefore treated as exploratory, not validated.

## Research conclusion

**Do not change the live RR10 router.**

The current evidence supports two separate objectives:

1. **Current fixed 3R**
   - stronger expectancy
   - lower 2024 drawdown
   - current canonical choice

2. **Adaptive C1**
   - higher hit rate
   - closer to ~8 trades/month
   - mostly 2R targets with occasional 3R/4R
   - promising as a separate research exit model

Adaptive C1 should remain **research-only** until it is validated on an additional unseen period / independent FxPro dataset.

The live TradingView / cBot RR10 strategy was not modified by this research.
