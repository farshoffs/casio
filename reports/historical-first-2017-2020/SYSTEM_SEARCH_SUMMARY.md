# CASIO Historical-First System Search — 2017–2020

Branch: `research/historical-2017-2020`

## Research protocol

Selection/development window is strictly 2017-01-01 through 2020-12-31 on the separate OctaFX/Octa Markets MT4 XAUUSD M5 historical feed.

2021+ is deliberately not used to select these systems.

Common execution:
- M15 execution unless stated otherwise.
- Fixed 3R target.
- Real structural stop; no protected-SL / breakeven manipulation.
- One position at a time.
- Same M5 bar SL + TP => SL first.
- 1 bp round-trip cost.
- RM100 starting equity.
- 5% current-equity risk per trade.

User objective:
- Prefer RR 1:3.
- Aim for at least ~8 trades/month, ideally no dead months.
- Positive multi-year performance, not one lucky year.
- Avoid catastrophic yearly drawdowns.
- High win rate is desirable, but no result should be disguised with artificial stop management.

## Pure systems that survived all four development years

### EMA Ribbon Break — non-Donchian

Rules:
- D1 and H4 trend aligned.
- M15 EMA8 > EMA20 > EMA50 for long (reverse for short).
- M15 breaks prior 10-bar high/low.
- M15 ADX >= 17.
- Structural stop.
- Fixed 3R.

Development:
- 327 trades.
- 6.81 trades/month average.
- 32.42% WR.
- +0.238R/trade.
- PF 1.33.
- Worst yearly DD 56.19%.
- RM100 -> RM1,245.30 across the continuous 2017–2020 development sequence.

Yearly:
| Year | Trades | WR | ExpR | PF | Max DD |
|---|---:|---:|---:|---:|---:|
| 2017 | 69 | 39.13% | +0.503 | 1.78 | 33.48% |
| 2018 | 88 | 27.27% | +0.024 | 1.03 | 52.46% |
| 2019 | 81 | 34.57% | +0.321 | 1.46 | 31.24% |
| 2020 | 89 | 30.34% | +0.167 | 1.23 | 56.19% |

Decision: strong independent core, but frequency below the user's desired level.

### D1 + H4 Aligned Donchian-10

Development:
- 454 trades.
- 9.46 trades/month average.
- 29.96% WR.
- +0.139R/trade.
- PF 1.19.
- Positive expectancy in all four years.
- Minimum month only 1 trade, so monthly frequency is not consistent.

Decision: valid core, but not the only family pursued.

### D1 + H4 Aligned Donchian-8

Development:
- 545 trades.
- 11.35 trades/month average.
- 29.17% WR.
- +0.107R/trade.
- PF 1.14.
- Positive expectancy in all four years.

Decision: higher-frequency Donchian core, but still has sparse individual months.

## Other non-Donchian family findings

### MACD + Ichimoku + EMA Ribbon portfolio

`PORT_TREND_ALT`

- 576 trades.
- 12.00 trades/month average.
- 30.56% WR.
- +0.154R/trade.
- PF 1.21.
- 4/4 positive years.
- Worst yearly expectancy +0.031R.
- Worst yearly DD 69.64%.
- RM100 -> RM825.78.

Yearly expectancy:
- 2017 +0.050R
- 2018 +0.031R
- 2019 +0.329R
- 2020 +0.210R

Decision: a genuine independent non-Donchian trend portfolio. Monthly minimum was only 2 trades.

### RSI(2) pullback

- 406 trades.
- 8.46 trades/month average.
- 30.54% WR.
- +0.103R/trade overall.
- 3/4 positive years.
- 2020 was slightly negative at -0.008R.

Decision: useful component, not a standalone robust system.

### Bollinger trend breakout

- 210 trades.
- 4.38 trades/month.
- 31.90% WR.
- +0.219R/trade.
- PF 1.30.
- 3/4 positive years.
- 2018 -0.064R.

Decision: high-quality auxiliary playbook but not standalone robust.

Keltner, ATR expansion, MACD standalone, Ichimoku standalone, ROC momentum, VWAP reclaim and basic London OR did not satisfy the multi-year robustness objective.

## Non-Donchian systems meeting the frequency consistency objective

### EMA Ribbon + raw Asia/NY session breakout

`EMA_RIBBON_PLUS_SESSION`

- Donchian excluded.
- 972 trades.
- 20.25 trades/month average.
- Minimum month = 8.
- 48/48 months had >=8 trades.
- 4/4 positive years.
- 29.73% WR.
- +0.131R/trade.
- PF 1.18.
- Worst yearly expectancy +0.074R.
- Worst yearly DD 79.47%.
- RM100 -> RM1,244.33 across the development sequence.

Yearly:
| Year | Trades | WR | ExpR | PF | Max DD |
|---|---:|---:|---:|---:|---:|
| 2017 | 241 | 31.54% | +0.195 | 1.27 | 62.87% |
| 2018 | 271 | 29.52% | +0.116 | 1.15 | 63.03% |
| 2019 | 209 | 30.14% | +0.145 | 1.20 | 79.47% |
| 2020 | 251 | 27.89% | +0.074 | 1.10 | 69.10% |

Decision: meets RR3, minimum monthly frequency and 4/4 positive-year requirements. Drawdown remains much too high for promotion.

### Trend Alternative + raw Asia/NY session breakout

`TREND_ALT_PLUS_SESSION`

Components:
- MACD continuation.
- Ichimoku continuation.
- EMA Ribbon breakout.
- Raw Asia breakout.
- Raw NY opening-range breakout.
- Donchian excluded.

Development:
- 1,143 trades.
- 23.81 trades/month average.
- Minimum month = 10.
- 48/48 months had >=8 trades.
- 4/4 positive years.
- 29.13% WR.
- +0.104R/trade.
- PF 1.14.
- Worst yearly expectancy +0.085R.
- Worst yearly DD 78.45%.
- RM100 -> RM438.12.

Yearly expectancy:
- 2017 +0.134R
- 2018 +0.086R
- 2019 +0.117R
- 2020 +0.085R

Decision: exceptionally consistent expectancy across the four development years and full monthly frequency coverage, but edge magnitude is modest and drawdown remains unacceptable at 5% risk.

## Donchian + session systems meeting frequency objective

For comparison:

`DON8_PLUS_SESSION`
- 1,106 trades.
- 23.04 trades/month.
- Minimum month = 10.
- 48/48 months >=8 trades.
- 4/4 positive years.
- 29.20% WR.
- +0.109R/trade.
- PF 1.15.
- Worst yearly expectancy +0.089R.
- Worst yearly DD 79.58%.

`DON10_PLUS_SESSION`
- 1,036 trades.
- 21.58 trades/month.
- Minimum month = 10.
- 48/48 months >=8 trades.
- 4/4 positive years.
- 29.05% WR.
- +0.104R/trade.
- PF 1.14.
- Worst yearly expectancy +0.073R.
- Worst yearly DD 82.19%.

These prove the monthly-frequency target is achievable, but do not solve risk quality.

## Stronger expectancy combinations that miss only a few low-frequency months

`EMA_RIBBON_BB_NY`
- 722 trades.
- 15.04 trades/month.
- Minimum month = 6.
- 45/48 months >=8 trades.
- 4/4 positive years.
- 30.47% WR.
- +0.167R/trade.
- PF 1.23.
- Worst yearly expectancy +0.050R.
- Worst DD 77.48%.

`EMA_RIBBON_RSI2_NY`
- 876 trades.
- 18.25 trades/month.
- Minimum month = 7.
- 45/48 months >=8 trades.
- 4/4 positive years.
- 30.25% WR.
- +0.142R/trade.
- PF 1.19.
- Worst yearly expectancy +0.036R.
- Worst DD 74.68%.

These have better average edge than the full-session portfolios, but miss the strict every-month frequency criterion in a few months.

## Current research conclusion

There are now multiple independent systems that are profitable in every development year 2017–2020.

The cleanest non-Donchian answer to the user's frequency target is:

`EMA_RIBBON_PLUS_SESSION`

The most stable year-to-year non-Donchian portfolio is:

`TREND_ALT_PLUS_SESSION`

The strongest pure non-Donchian core by expectancy is:

`EMA_RIBBON_BREAK`

None should be promoted yet because the 5% risk model still creates 56–79% yearly drawdowns. The next research problem is therefore no longer “find an edge”; it is “reduce drawdown while preserving 4/4 positive years and >=8 monthly trades.”

2021+ remains sealed and must only be opened after a final development rule is frozen.
