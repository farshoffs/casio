# CASIO Hybrid Core v1 — Clean Event Router + Shadow Health Gate

Date: 2026-09-24

## Objective
Build a CASIO-native strategy from components that repeatedly survived earlier audits, without relying on branded strategy labels or the flawed source-position preblocking used by the old Regime Router.

## Data / execution
- User-supplied FxPro XAUUSD M1, 2017-01-02 through 2026-09-24
- completed H1/H4 only
- M15 setup events
- M1 execution / chronological SL-TP resolution
- fixed 3R
- real structural SL only
- no BE / protected SL
- one live portfolio trade at a time
- main robustness result includes 1 bp round-trip cost sensitivity

## Architecture
H4 = regime / directional context
H1 = veto against double-opposition
M15 = setup event
M1 = execution

Retained source modules:
1. V1 momentum: M15 EMA20/50 trend + 10-bar breakout + directional body quality.
2. Structural Frequency: H1/H4 not opposed + recent M15 sweep + displacement/FVG + original primary-session rule.

Setup events are explicit false->true transitions with a two-M15-bar same-module/direction cooldown. This replaces source-technique hypothetical position preblocking.

Router:
- strong H1/H4 trend + H4 ADX >=18: trend direction only, V1 priority then Structural Frequency
- mixed regime: Structural Frequency first; V1 requires same-direction Structural Frequency support in prior 30m
- reject when completed H1 and H4 both oppose

## Stage 1 — modular audit
The strongest simple module (H4 EMA + H1 veto + M15 continuation/value + developed M1 confirmation) produced 1,105 trades and +29.48R after 1 bp, PF 1.035, only 6/10 positive years.

A bounded 32-variant walk-forward filter study used 2017-2022 as development and 2023-2025 / 2026 as later blocks. No candidate passed the predeclared development gate. No winner was promoted.

## Stage 2 — clean event router
- 2,222 trades
- 27.81% gross target WR
- +151.16R after 1 bp
- +0.068R/trade
- PF 1.090
- 6/10 positive years
- 2021 = -55.84R
- 1% risk: RM100 -> RM318.63, max DD 60.9%
- 5% risk: RM100 -> RM42.50, max DD 99.8%

## Stage 3 — shadow health gate
Every valid V1/SF setup is tracked in a shadow ledger whether traded or not. At a new signal:
- only already-closed shadow setups are eligible
- trailing window = 180 calendar days
- minimum 20 completed shadow setups for the module
- module enabled only if trailing completed shadow net-R sum is positive
- no change to an open trade, stop, or target

### Full-history result after 1 bp
- trades: 1,296
- gross target WR: 29.09%
- net R: +157.56R
- expectancy: +0.1216R/trade
- PF: 1.165
- positive years: 8/10
- worst year: 2018, -12.69R
- 2021 improves from -55.84R to +2.73R

### Yearly
| Year | Trades | WR | Net R | PF |
|---:|---:|---:|---:|---:|
| 2017 | 162 | 33.95% | +48.42R | 1.428 |
| 2018 | 122 | 23.77% | -12.69R | 0.870 |
| 2019 | 95 | 28.42% | +7.81R | 1.109 |
| 2020 | 167 | 28.74% | +19.33R | 1.157 |
| 2021 | 90 | 26.67% | +2.73R | 1.040 |
| 2022 | 87 | 28.74% | +9.67R | 1.150 |
| 2023 | 92 | 28.26% | +7.55R | 1.109 |
| 2024 | 139 | 24.46% | -9.57R | 0.913 |
| 2025 | 164 | 32.32% | +42.40R | 1.369 |
| 2026 YTD | 178 | 31.46% | +41.92R | 1.336 |

### Module contribution
- V1: 730 trades, 29.86% WR, +110.37R after 1 bp
- Structural Frequency: 566 trades, 28.09% WR, +47.19R after 1 bp

### Cost sensitivity
| Cost | Net R | PF | RM100 @ 1% | Max DD @ 1% |
|---:|---:|---:|---:|---:|
| 0 bp | +212.00R | 1.231 | RM673.56 | 17.68% |
| 0.5 bp | +184.78R | 1.197 | RM513.27 | 20.07% |
| 1.0 bp | +157.56R | 1.165 | RM391.10 | 22.98% |
| 1.5 bp | +130.34R | 1.134 | RM297.98 | 26.36% |
| 2.0 bp | +103.12R | 1.104 | RM227.02 | 30.42% |

### Risk sensitivity at 1 bp
- 0.5% risk: RM100 -> RM208.44, max DD 11.77%
- 1% risk: RM100 -> RM391.10, max DD 22.98%
- 2% risk: RM100 -> RM1,012.13, max DD 43.13%
- 5% risk: RM100 -> RM1,698.10, max DD 90.73%

5% sizing is rejected for production due path risk.

### Frequency
Across 115 completed audit months:
- avg 11.03 trades/month
- median 11
- minimum 0
- 79/115 months >=8 trades
- 10 zero-trade completed months

2026 YTD monthly trades:
Jan 23, Feb 17, Mar 21, Apr 16, May 23, Jun 24, Jul 20, Aug 20, Sep YTD 14.

## Production gate
PASS:
- causal completed HTF
- M1 execution
- real SL / no protected SL
- fixed 3R
- positive after 1 bp
- 8/10 positive years
- <=30% DD at 1% risk

FAIL / incomplete:
- PF >=1.25 after 1 bp: FAIL (1.165)
- >=8 trades every completed month: FAIL (79/115)
- independent-feed validation: not yet tested
- untouched forward validation: not yet tested

## Decision
CASIO Hybrid Core v1 is a serious research candidate, **not production-ready**.

No more parameter tuning should be performed on the FxPro 2017-2026 file. The next valid evidence should come from an independent feed or future unseen data.
