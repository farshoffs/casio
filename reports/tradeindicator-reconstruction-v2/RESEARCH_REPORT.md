# CASIO TradeIndicator Reconstruction v2 — XAUUSD FxPro M1

Date: 2026-09-25

## Scope

Full user-supplied FxPro XAUUSD M1 history: 2017-01-02 through 2026-09-24.

Execution assumptions retained from v1:
- H1 confirmed pivot zones become active only after right-side confirmation bars close
- M15 signal logic, next M1 open execution
- real structural SL
- fixed 3R target
- stop-first if SL and TP touch the same M1 bar
- one active position at a time
- no BE, protected stop, partial profit, averaging or layering
- RM100, 5% current-equity risk

Research split:
- Train: 2017-2021
- Validation: 2022-2024
- 2025-2026 used as a pseudo-holdout stability check. It is not pristine OOS because this historical dataset has already been inspected in earlier CASIO research.

## V1 long-sleeve baseline

With only Demand Rejection BUY + Supply Break/Hold BUY enabled and replayed as a proper long-only system:
- 1,647 trades
- 28.35% WR
- +0.134R/trade
- PF 1.187
- +221R gross
- 93.77% max DD at 5% risk

Performance decayed across time:
- Train: +0.195R/trade
- Validation: +0.084R/trade
- Pseudo-holdout: +0.052R/trade

## Stable causal filters found

Demand rejection:
1. H1 bullish trend: close > EMA20 > EMA50 and EMA20 rising
2. M15 rejection candle closes in the upper 35% of its range (close-location >= 0.65)

Supply break/hold:
1. signal occurs during 08:00-17:00 New York local time (DST-aware)
2. H1 ADX >= 20

This creates **QUALITY_V2**.

## QUALITY_V2

| Split | Trades | WR | Exp/trade | PF | Net R | RM100 reset -> | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017-2021 | 313 | 30.67% | +0.227R | 1.327 | +71R | RM984.05 | 52.41% |
| 2022-2024 | 193 | 30.57% | +0.223R | 1.321 | +43R | RM394.58 | 64.07% |
| 2025-2026 | 118 | 36.44% | +0.458R | 1.720 | +54R | RM869.52 | 48.93% |
| Full | 624 | 31.73% | **+0.269R** | **1.394** | **+168R** | continuous RM100 -> **RM33,762** | **64.07%** |

### Sleeve contribution

Demand Rejection BUY + H1 bull trend + strong M15 close:
- 259 trades
- 32.43% WR
- +0.297R/trade
- PF 1.44
- +77R

Supply Break/Hold BUY + NY session + H1 ADX >=20:
- 365 trades
- 31.23% WR
- +0.249R/trade
- PF 1.36
- +91R

### Calendar years

| Year | Trades | WR | Exp/trade | PF | Net R | RM100 reset -> | DD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 70 | 35.71% | +0.429R | 1.67 | +30R | RM327.35 | 40.13% |
| 2018 | 60 | 26.67% | +0.067R | 1.09 | +4R | RM97.95 | 47.47% |
| 2019 | 54 | 31.48% | +0.259R | 1.38 | +14R | RM161.30 | 38.73% |
| 2020 | 73 | 30.14% | +0.205R | 1.29 | +15R | RM158.22 | 45.48% |
| 2021 | 56 | 28.57% | +0.143R | 1.20 | +8R | RM120.26 | 36.98% |
| 2022 | 66 | 22.73% | **-0.091R** | 0.88 | -6R | RM59.48 | 61.78% |
| 2023 | 58 | 32.76% | +0.310R | 1.46 | +18R | RM192.52 | 49.39% |
| 2024 | 69 | 36.23% | +0.449R | 1.70 | +31R | RM344.58 | 27.52% |
| 2025 | 60 | 43.33% | +0.733R | 2.29 | +44R | RM661.83 | 30.17% |
| 2026 YTD | 58 | 29.31% | +0.172R | 1.24 | +10R | RM131.38 | 48.93% |

### Cost stress

| Cost/trade | Exp/trade | PF | Continuous RM100 -> | DD |
|---:|---:|---:|---:|---:|
| 0.00R | +0.269R | 1.394 | RM33,762 | 64.07% |
| 0.02R | +0.249R | 1.358 | RM18,146 | 67.11% |
| 0.05R | +0.219R | 1.306 | RM7,141 | 71.19% |
| 0.10R | +0.169R | 1.225 | RM1,505 | 81.42% |

Generic R-cost stress; this is not a broker-exact spread model.

### Frequency

2017-01 through 2026-08 completed-month window:
- 5.35 trades/month average
- median 5/month
- minimum 1/month
- 18/116 months >=8 trades
- 91/116 months >=4 trades

QUALITY_V2 fails the strict >=8 trades/month requirement.

## Neighborhood robustness

Nearby parameters tested:
- demand M15 close-location: 0.60 / 0.65 / 0.70
- supply H1 ADX: 18 / 20 / 22

All 9 combinations remained positive in train, validation and pseudo-holdout.

Across the 9 full-history variants:
- expectancy about +0.235R to +0.268R/trade
- PF about 1.34 to 1.39
- DD about 61% to 68% for most variants

This reduces concern that close-location 0.65 or ADX 20 is a single fitted number.

## Frequency-oriented variants

### BALANCED_V2
Demand strong close >=0.65 + Supply breakout with nonnegative M15 relative-volume z-score.

- 1,233 trades
- 29.52% WR
- +0.181R/trade
- PF 1.257
- 10.56 trades/month average
- 98/116 completed months >=8
- minimum month 3
- 87.84% max DD at 5%
- negative 2018, 2022 and 2026 YTD

### FREQ_V2
All demand-rejection buys + supply break/hold only when volume z >=0.

- 1,276 trades
- 29.47% WR
- +0.179R/trade
- PF 1.253
- 10.93 trades/month average
- 102/116 completed months >=8
- minimum month 3
- 87.43% max DD at 5%
- negative 2018, 2022 and 2026 YTD

## Current decision

- Keep QUALITY_V2 as a research candidate.
- Do not promote at 5% risk because max DD remains about 64% gross and exceeds 70% under 0.05R stress.
- Do not loosen it just to hit 8 trades/month; the frequency versions restore destructive losing sequences.
- Freeze the architecture and validate on an independent broker/feed or forward sample rather than continue optimizing this same FxPro history.
