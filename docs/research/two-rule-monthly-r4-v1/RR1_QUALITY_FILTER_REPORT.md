# CASIO M5 Sweep Quality + 1R Monthly Lock

## Current hard rules

1. Minimum 8 completed/accepted trades per completed calendar month.
2. Minimum +4R net per completed calendar month.
3. Winners > losers in every completed calendar month.

Because every trade is fixed +1R / -1R, rule 2 implies rule 3 whenever +4R is achieved.

## Method

Base family: M5 liquidity sweep -> reclaim -> M1 micro-BOS confirmation -> structural stop -> fixed 1R.

Winner/loser quality variables were restricted to information known before entry. The A-grade grid included:
- sweep lookback;
- rejection-wick fraction;
- reclaim close location;
- M1 confirmation candle body fraction;
- structural stop size normalized by M5 ATR;
- H1 RSI overextension against the incoming sweep direction;
- distance from M5 EMA20 normalized by ATR;
- all-session vs primary-session filter.

Top eight frozen quality variants per market were combined across XAUUSD, EURUSD, GBPUSD and GBPJPY. 4,096 four-market portfolios were tested.

Monthly lock is causal on realized exits: the router stops opening new trades only after at least 8 trades have actually closed and realized monthly R is >= +4R. Positions already open at the lock are allowed to finish and their final R still counts to the month.

A second development-only weekday-quality filter was applied. For each selected market/variant, weekdays were permitted only if their 2017-2022 win rate was at least 50.5% with >=100 development trades.

## Best result

- Completed months: 116 (Jan 2017 through Aug 2026)
- Passing months: 110 / 116
- Failing months: 6
- Accepted trades: 7,896
- Portfolio WR: 52.08%
- Net R across accepted trades: +328R
- 2026 completed months passing: 8 / 8

### Failed months

| Month | Trades | Wins | Losses | WR | Net R |
|---|---:|---:|---:|---:|---:|
| 2017-12 | 290 | 131 | 159 | 45.17% | -28R |
| 2018-08 | 357 | 171 | 186 | 47.90% | -15R |
| 2018-11 | 319 | 148 | 171 | 46.39% | -23R |
| 2022-03 | 326 | 151 | 175 | 46.32% | -24R |
| 2022-07 | 298 | 136 | 162 | 45.64% | -26R |
| 2024-11 | 325 | 151 | 174 | 46.46% | -23R |

### 2026

| Month | Trades | Wins | Losses | WR | Net R |
|---|---:|---:|---:|---:|---:|
| Jan | 164 | 84 | 80 | 51.22% | +4R |
| Feb | 20 | 12 | 8 | 60.00% | +4R |
| Mar | 110 | 57 | 53 | 51.82% | +4R |
| Apr | 32 | 18 | 14 | 56.25% | +4R |
| May | 82 | 43 | 39 | 52.44% | +4R |
| Jun | 18 | 11 | 7 | 61.11% | +4R |
| Jul | 48 | 26 | 22 | 54.17% | +4R |
| Aug | 9 | 7 | 2 | 77.78% | +5R |

## Frozen weekday-quality rules

- XAUUSD selected variant 1: allow Monday, Tuesday, Wednesday.
- EURUSD selected variant 1: allow Monday, Tuesday, Wednesday, Friday.
- GBPUSD selected variant 4: allow Monday-Friday.
- GBPJPY selected variant 1: allow Tuesday-Friday.

## Verdict

The quality analysis improved the four-market monthly result from 107/116 to 110/116 and pushed the accepted-trade WR above 52%, with all completed 2026 months passing. However the requested historical rule is absolute, and six completed months still fail. Therefore this version is **REJECTED as a full-rule pass**.

No month-specific exceptions were added.
