# CASIO FX Cadence Router v1

Date: 2026-09-25

## User gate
- RM100 start
- 5% current-equity risk per accepted entry
- fixed 3R
- WR 30%-40%
- PF 1.5-1.9
- >=8 trades in every completed month
- real SL only
- no BE / protected SL
- EURUSD + GBPUSD + GBPJPY
- FxPro M1, 2017-2026 YTD
- causal MTF / M1 execution

## Frozen architecture

### A. NY MTF Precision
Always eligible:
- H1/H4 direction aligned
- NY AM
- M5 ADX >=28
- tick-volume ratio >=1.0
- body >=1.0 ATR
- body/range >=0.72
- break prior 8 M5 bars
- 70.5% retracement
- M1 micro-BOS confirmation
- structural M1 stop
- fixed 3R

### B. FiboRSI Primary
- M15 RSI8 crosses below 23 for buy / above 77 for sell
- buy trigger candle bearish / sell trigger candle bullish
- completed M30 RSI8 >=32.5 buy / <=67.5 sell
- next available M1 open after M15 close
- SL at trigger M15 opposite wick
- fixed 3R
- UTC entry hours: 19, 21, 22, 23

### C. FiboRSI Cadence Fallback
Same FiboRSI rules.
- fallback UTC hours: 00, 02, 04, 05, 06, 07, 15, 20
- activates from day 20 onward only while portfolio has <8 accepted entries that month
- stops fallback entries once monthly count reaches 8
- primary and precision sleeves remain eligible
- one open position per pair; different pairs may be concurrent

This fallback is causal. It changes no open trade, stop, target or result.

## Full-history gross result
- Trades: 1,153
- Wins: 414
- Losses: 739
- WR: 35.91%
- PF: 1.681
- Gross R: +503R
- Completed-month average through Aug-2026: 9.86
- Completed-month minimum: 8
- 116/116 completed months >=8
- Gross-positive years: 10/10
- Longest win streak: 8
- Longest loss streak: 15

## Development / validation
2017-2022 development:
- 710 trades
- WR 37.32%
- PF 1.787
- min completed month 8

2023-2026 YTD later validation:
- 443 trades
- WR 33.63%
- PF 1.520
- min completed month 8

Both blocks pass the requested gross WR/PF/frequency gate.

## Sleeve contribution
| Sleeve | Trades | WR | PF | Gross R |
|---|---:|---:|---:|---:|
| FiboRSI Primary | 653 | 38.28% | 1.861 | +347R |
| NY MTF Precision | 108 | 34.26% | 1.563 | +40R |
| FiboRSI Fallback | 392 | 32.40% | 1.438 | +116R |

## Yearly gross
| Year | Trades | WR | PF | Gross R | RM100 reset @5% | Max DD |
|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 125 | 35.20% | 1.630 | +51R | RM735.05 | 35.50% |
| 2018 | 120 | 33.33% | 1.500 | +40R | RM442.39 | 48.47% |
| 2019 | 111 | 37.84% | 1.826 | +57R | RM1,028.58 | 36.98% |
| 2020 | 124 | 39.52% | 1.960 | +72R | RM2,011.24 | 33.66% |
| 2021 | 113 | 35.40% | 1.644 | +47R | RM633.49 | 57.43% |
| 2022 | 117 | 42.74% | 2.239 | +83R | RM3,486.37 | 33.66% |
| 2023 | 112 | 33.93% | 1.541 | +40R | RM455.06 | 33.66% |
| 2024 | 113 | 30.09% | 1.291 | +23R | RM201.32 | 59.35% |
| 2025 | 129 | 32.56% | 1.448 | +39R | RM408.57 | 51.48% |
| 2026 YTD | 89 | 39.33% | 1.944 | +51R | RM834.64 | 43.12% |

All ten year rows are gross-positive.

## Continuous RM100 risk sensitivity
- 0.5% risk: RM1,170.03, 8.78% max DD
- 1% risk: RM12,274.95, 17.09% max DD
- 2% risk: RM983,327.44, 32.25% max DD
- 5% risk: RM46,414,130,056.71, 65.99% max DD

5% passes profitability but remains extremely aggressive.

## Cost sensitivity
The existing CASIO cost stress converts price friction into R from each trade's actual stop distance.

| Cost | PF | Net R | RM100 @5% | Max DD |
|---:|---:|---:|---:|---:|
| 0.00 bp | 1.681 | +503.0R | RM46,414,130,056.71 | 65.99% |
| 0.10 bp | 1.370 | +318.7R | RM4,403,901.75 | 88.11% |
| 0.25 bp | 1.040 | +42.3R | RM2.36 | 99.66% |
| 0.50 bp | 0.695 | -418.5R | ~RM0 | 100% |
| 1.00 bp | 0.363 | -1,340.0R | ~RM0 | 100% |

## Verdict
PASS against the requested **gross** backtest gate:
- WR 30%-40%: PASS
- fixed 3R: PASS
- PF 1.5-1.9: PASS
- >=8 trades every completed month: PASS
- 10/10 gross-positive years: PASS
- causal MTF/M1: PASS
- real SL / no protected stop: PASS
- development and later validation both pass WR/PF/frequency: PASS

Production caveat: the generic cost stress fails badly because the FiboRSI wick stops can be very tight. Before deployment, use actual broker bid/ask or realistic per-pair spread+commission and verify execution without changing the historical rules.
