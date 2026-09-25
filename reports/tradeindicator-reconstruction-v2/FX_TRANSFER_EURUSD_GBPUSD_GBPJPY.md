# CASIO TradeIndicator FINAL V3 — FX Transfer Backtest

Date: 2026-09-25

Data: user-supplied FxPro M1, EURUSD / GBPUSD / GBPJPY, 2017-01-01 through 2026-09-24.

Rules were transferred from frozen XAUUSD FINAL V3 without pair-specific retuning:
- H4/H1/M15 causal context
- H1 supply/demand zone sleeves
- Tick-M15 H4-aligned long sleeve
- M1 execution chronology
- one active portfolio position
- real structural SL
- fixed 3R
- same-M1 SL/TP collision = SL
- no BE / protected SL / partial / averaging
- RM100, 5% current-equity risk

Implementation cross-check: regenerated XAUUSD produced 1,016 trades vs 1,013 frozen trades, with the same ~51.9% max DD. The transfer engine therefore reproduces the frozen architecture very closely, though it is not byte-for-byte identical to the original zone-signal generator.

## Headline

| Pair | Trades | W-L | WR | Net R | Exp/trade | PF | Avg/month | RM100 -> | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 981 | 241-740 | 24.57% | -17R | -0.017R | 0.977 | 8.41 | RM1.39 | 99.83% |
| GBPUSD | 956 | 242-714 | 25.31% | +12R | +0.013R | 1.017 | 8.20 | RM6.07 | 99.39% |
| GBPJPY | 916 | 232-684 | 25.33% | +12R | +0.013R | 1.018 | 7.87 | RM7.00 | 98.92% |

The frozen XAUUSD portfolio does not transfer as a complete system to these three FX pairs. EURUSD is negative before costs; GBPUSD and GBPJPY are only marginally positive before costs. A 0.02R generic friction stress makes all three negative.

## Chronological split

### EURUSD
- 2017–2021: 527 trades, WR 23.53%, -31R, -0.059R/trade, PF 0.923
- 2022–2024: 288 trades, 25.00% WR, 0R, 0.000R/trade, PF 1.000
- 2025–2026: 166 trades, 27.11% WR, +14R, +0.084R/trade, PF 1.116

### GBPUSD
- 2017–2021: 516 trades, WR 26.36%, +28R, +0.054R/trade, PF 1.074
- 2022–2024: 278 trades, 24.10% WR, -10R, -0.036R/trade, PF 0.953
- 2025–2026: 162 trades, 24.07% WR, -6R, -0.037R/trade, PF 0.951

### GBPJPY
- 2017–2021: 496 trades, WR 28.02%, +60R, +0.121R/trade, PF 1.168
- 2022–2024: 272 trades, 22.79% WR, -24R, -0.088R/trade, PF 0.886
- 2025–2026: 148 trades, 20.95% WR, -24R, -0.162R/trade, PF 0.795

## Sleeve contribution inside exact portfolio

EURUSD:
- Demand Breakdown SELL: +17R, +0.060R/trade, PF 1.082
- Demand Rejection BUY: -9R, -0.062R/trade, PF 0.919
- Supply Break & Hold BUY: -40R, -0.139R/trade, PF 0.823
- Tick-M15 H4 Long: +15R, +0.057R/trade, PF 1.077

GBPUSD:
- Demand Breakdown SELL: +16R, +0.059R/trade, PF 1.080
- Demand Rejection BUY: +19R, +0.101R/trade, PF 1.139
- Supply Break & Hold BUY: +1R, +0.004R/trade, PF 1.005
- Tick-M15 H4 Long: -24R, -0.100R/trade, PF 0.871

GBPJPY:
- Demand Breakdown SELL: +4R, +0.016R/trade, PF 1.022
- Demand Rejection BUY: -7R, -0.030R/trade, PF 0.960
- Supply Break & Hold BUY: -29R, -0.122R/trade, PF 0.843
- Tick-M15 H4 Long: +44R, +0.216R/trade, PF 1.310

## 2026 YTD

- EURUSD: 66 trades, 20W/46L, 30.30% WR, +14R, +0.212R/trade, PF 1.304, RM100 -> RM154.61, DD 47.5%
- GBPUSD: 59 trades, 10W/49L, 16.95% WR, -19R, -0.322R/trade, PF 0.612, RM100 -> RM32.77, DD 76.7%
- GBPJPY: 64 trades, 16W/48L, 25.00% WR, 0R, PF 1.000, RM100 -> RM79.78, DD 57.4%

## Cost stress

At 0.02R generic friction:
- EURUSD: -36.62R, -0.037R/trade, PF 0.951
- GBPUSD: -7.12R, -0.007R/trade, PF 0.990
- GBPJPY: -6.32R, -0.007R/trade, PF 0.991

## Decision

Do not deploy FINAL V3 unchanged on EURUSD, GBPUSD, or GBPJPY.

The full architecture remains XAUUSD-specific. The one research lead worth preserving is GBPJPY Tick-M15 H4 Long (+44R, +0.216R/trade, PF 1.31 within the transferred portfolio), but it requires its own standalone robustness test before any promotion.
