# CASIO TradeIndicator Portfolio V3 — FxPro XAUUSD M1

Date: 2026-09-25

Dataset: user-supplied FxPro XAUUSD M1, 2017-01-02 through 2026-09-24.

Execution:
- causal H1/H4/M15 context
- M1 chronological execution
- one active position across all sleeves
- fixed 3R target
- real structural stop
- same-M1 SL/TP collision = SL first
- no BE, protected stop, partials or averaging

## Frozen sleeves

### 1. TradeIndicator Quality V2.1 — Demand Rejection BUY
- H1 bullish trend
- strong M15 bullish rejection close
- zone prior touches <=3

### 2. TradeIndicator Quality V2.1 — Supply Break & Hold BUY
- resistance accepted / break-hold structure
- New York session
- H1 ADX >=20
- zone prior touches <=3

### 3. Bearish Breakdown VOL0 SELL
- Demand/support break-hold SELL
- H1 -DI > +DI
- price 0.75-2.0 H1 ATR below EMA20
- prior touches <=4
- signal tick-volume z-score >=0

### 4. M15 Tick-Volume H4-Aligned LONG
- H1 EMA20 > EMA50 and close > EMA20
- H4 EMA20 > EMA50 and close > EMA20
- M15 tick-volume z-score >=2.5 over 50 bars
- M15 body >=55% of range
- M15 range >=0.8 ATR14
- close in top 30%
- break previous 10 M15 highs
- stop below impulse low by 0.10 ATR
- fixed 3R

Priority for simultaneous signals:
1. V2.1 zone engine
2. Bearish Breakdown VOL0
3. Tick-volume long

If another sleeve signals while a trade is active, the signal is skipped.

## Portfolio result

| Metric | V2.1 only | V2.1 + Short VOL0 | Portfolio V3 |
|---|---:|---:|---:|
| Trades | 548 | 822 | **1,013** |
| Average trades/month | 4.70 | 7.03 | **8.67** |
| Median trades/month | 4 | 7 | **8** |
| Win rate | 32.66% | 31.75% | **32.68%** |
| Expectancy | +0.307R | +0.270R | **+0.307R** |
| PF | 1.455 | 1.396 | **1.456** |
| Net R | +168R | +222R | **+311R** |
| Max DD @5% | 53.74% | **45.48%** | 51.92% |
| Longest loss streak | 10 | 11 | 12 |

Portfolio V3 achieves the target average frequency without sacrificing aggregate expectancy versus V2.1.

Frequency distribution over Jan-2017 through Aug-2026:
- average 8.67 trades/month
- median 8
- 75 / 116 months >=8 trades
- 109 / 116 months >=5 trades
- no zero-trade months
- minimum month = 1 trade

It does **not** satisfy a literal minimum-8-trades-every-month rule.

## Chronological splits

| Split | Trades | WR | Exp/trade | PF | Net R | Max DD @5% |
|---|---:|---:|---:|---:|---:|---:|
| 2017-2021 train | 531 | 31.07% | +0.243R | 1.352 | +129R | 50.68% |
| 2022-2024 validation | 305 | 33.77% | **+0.351R** | 1.530 | +107R | 42.61% |
| 2025-2026 pseudo-holdout | 177 | 35.59% | **+0.424R** | 1.658 | +75R | 51.92% |

No split collapses.

## Calendar-year arithmetic

Every calendar year is positive in arithmetic R:

| Year | Trades | WR | Exp/trade | Net R | PF | RM100 reset -> | Max DD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 120 | 39.17% | +0.567R | +68R | 1.93 | RM1,685 | 45.96% |
| 2018 | 99 | 26.26% | +0.051R | +5R | 1.07 | RM89.53 | 45.27% |
| 2019 | 104 | 30.77% | +0.231R | +24R | 1.33 | RM217.99 | 48.20% |
| 2020 | 111 | 30.63% | +0.225R | +25R | 1.32 | RM223.07 | 31.15% |
| 2021 | 97 | 26.80% | +0.072R | +7R | 1.10 | RM99.20 | 38.73% |
| 2022 | 88 | 35.23% | +0.409R | +36R | 1.63 | RM409.15 | 32.11% |
| 2023 | 107 | 31.78% | +0.271R | +29R | 1.40 | RM273.87 | 37.30% |
| 2024 | 110 | 34.55% | +0.382R | +42R | 1.58 | RM504.22 | 38.18% |
| 2025 | 104 | 37.50% | +0.500R | +52R | 1.80 | RM830.33 | 51.92% |
| 2026 YTD | 73 | 32.88% | +0.315R | +23R | 1.47 | RM231.85 | 40.97% |

2018 and 2021 are important reminders that positive arithmetic R does not guarantee positive 5%-risk compounded return because sequence/volatility drag matters.

## 2026 YTD monthly

- Jan: 18 trades, +2R
- Feb: 11 trades, +9R
- Mar: 6 trades, +6R
- Apr: 6 trades, +2R
- May: 8 trades, -4R
- Jun: 8 trades, -4R
- Jul: 5 trades, +3R
- Aug: 4 trades, +8R
- Sep through Sep 24: 7 trades, +1R

## Sleeve contribution inside exact portfolio

| Sleeve | Trades | Exp/trade | Net R |
|---|---:|---:|---:|
| Demand Rejection BUY | 172 | +0.395R | +68R |
| Supply Break & Hold BUY | 303 | +0.241R | +73R |
| Bearish Breakdown VOL0 SELL | 262 | +0.191R | +50R |
| Tick-M15 H4 Long | 276 | **+0.435R** | **+120R** |

All four sleeves contribute positive R in the exact one-position portfolio.

## Diversification

Monthly arithmetic-R correlations between standalone sleeves:

- V2.1 vs Short VOL0: **-0.186**
- V2.1 vs Tick Long: **+0.067**
- Short VOL0 vs Tick Long: **+0.037**

This is the strongest structural argument for the portfolio: the added sleeves are not simply duplicating the same monthly P&L stream.

## Cost stress

Portfolio V3:

- 0.00R cost/trade: +0.307R/trade, PF 1.456
- 0.02R cost: +0.287R/trade, PF 1.418
- 0.05R cost: +0.257R/trade, PF 1.364
- 0.10R cost: +0.207R/trade, PF 1.280

The edge remains positive under substantial generic R-friction stress.

## Risk stress

Same frozen trade sequence:

| Risk/trade | Max DD | Continuous RM100 ending* |
|---:|---:|---:|
| 1% | 13.18% | RM1,872 |
| 2% | 24.81% | RM24,685 |
| 3% | 35.05% | RM232,538 |
| 4% | 44.05% | RM1,585,428 |
| 5% | 51.92% | RM7,915,602 |

*Mechanical compounding illustration only; not a forecast and excludes real broker sizing limits / execution frictions.

## Decision

Freeze **CASIO TradeIndicator Portfolio V3** as a research candidate.

Reasons:
1. >8 trades/month average and median 8;
2. +0.307R/trade at fixed 3R;
3. PF 1.456;
4. all three chronological splits remain positive;
5. every calendar year is positive in arithmetic R;
6. low monthly correlation between sleeves;
7. cost stress remains positive;
8. no protected-stop or management manipulation.

Remaining failures / cautions:
- only 75/116 months reach >=8 trades; min month is 1;
- 5%-risk max DD remains ~52%;
- 2017-2026 has been repeatedly inspected during CASIO research and is no longer pristine out-of-sample;
- RM compounding figures should not be treated as expected future wealth.

Do not optimize this historical sample further. Next step should be frozen forward/paper validation and realistic FxPro spread/commission/slippage modelling.
