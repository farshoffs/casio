# RR10 Post-Entry Behaviour Study — 2017 Onward

## Scope

Research only. No live RR10 strategy files were changed.

Frozen canonical RR10:
- M15 0591 entry
- H1/H4 MTF router
- TREND/MIXED logic
- structural 0591 stop
- fixed 3R target
- one active trade
- 5% current-equity risk

Data:
- FxPro M15: 229,303 bars, 2017-01-02 -> 2026-09-18
- FxPro M5: 687,746 bars, same broker/feed family
- post-entry path measured on genuine M5 bars
- full collection: 796 closed canonical trades
- comparable research sample: 784 closed trades from 2017-03-04 onward

## What was collected for every trade

- MFE in R
- MAE in R
- time to MFE / MAE
- time to +0.5R / +1R / +1.5R / +2R / +2.5R / +3R
- whether eventual losers first moved +0.5R in favour
- total trade duration
- current day range at entry
- 20-day ADR
- directional range already consumed at entry
- projected daily range required to complete 3R
- H1/H4/D1 completed bias
- H1/H4/D1 bias age
- H4 and D1 extension in ATR units
- D1 ADX
- M15 stop distance / ATR
- exact 0591 impulse range / ATR and body fraction

## Core post-entry finding

2017-2023 had 540 canonical trades:
- 24.63% win rate
- -0.015R expectancy
- PF 0.98

Yet among **eventual losing trades**:
- 57.74% reached +0.5R before stopping
- 33.91% reached +1R
- 22.36% reached +1.5R
- 13.02% reached +2R
- loser median MFE: +0.651R

For 2018 + 2022 specifically:
- 59.85% of losers reached +0.5R
- 37.12% reached +1R
- 24.24% reached +1.5R
- 12.12% reached +2R
- loser median MFE: +0.727R

This is strong evidence that a meaningful portion of historical damage came from **giving back initially favourable movement**, not simply from entries being wrong immediately.

## Time-stop hypothesis

The data does not strongly support a simple time-stop.

Typical losers resolve faster than winners.

Examples:
- 2018 winner median duration: 4.25h; loser: 2.88h
- 2020 winner: 7.38h; loser: 3.50h
- 2022 winner: 6.25h; loser: 2.13h
- 2024 winner: 12.0h; loser: 2.75h

A blunt time-stop therefore risks cutting eventual winners more than losers.

## ADR / remaining-range hypothesis

The user's observation that older gold moved fewer nominal points is real, but **lack of daily range is not the main reason fixed 3R failed**.

2017-2023:
- median projected daily range needed to complete 3R: ~0.91 ADR
- 43.52% of trades required >1 ADR total daily range

2024-2026:
- median projected daily range needed: ~1.08 ADR
- 56.56% required >1 ADR

The recent profitable regime actually asks the market to complete larger ADR-relative moves more often.

Therefore "3R target is too far because old daily range was smaller" is not supported as a standalone explanation.

## D1 / H4 context findings

A hard D1-alignment filter is not robust.

2017-2023:
- D1 aligned with trade: -0.155R expectancy
- D1 not aligned: +0.120R

2024-2026 reverses:
- D1 aligned: +0.707R
- D1 not aligned: +0.471R

Likewise, the assumption that old failures were mainly late-cycle H4 trends is not supported. H4 bias age >=16 bars was actually positive in 2017-2023.

One interesting transition-state clue remains:
- D1 bias age 2-3 completed daily bars
- 68 trades over 2017-2026
- 19.12% WR
- -0.235R average expectancy

But sample behaviour varies by year and router mode, so it is not ready as a deployment rule.

## Trade-management diagnostics

These diagnostics move a stop only from the **next M5 bar after the trigger**, avoiding same-bar lookahead.

Always applying breakeven at +0.5R would improve 2017-2023 but damage modern expectancy badly.

Trade-level diagnostic:
- 2017-2023 baseline: -0.015R -> BE0.5: +0.085R
- 2018+2022: -0.124R -> +0.077R
- 2024-2026: +0.623R -> +0.299R

So universal breakeven is not acceptable.

## Pace-dependent protection

The manual observation about market speed becomes useful when expressed as an observable entry-time variable:

**M15 ATR as % of price**

Research rule:
- normal/faster market: canonical RR10, no management change
- slow market: after price reaches +0.5R, move stop to breakeven starting with the next M5 bar

This changes **trade management only**, not entry/router/initial SL/3R TP.

### Sequential replay — threshold 0.13%

Slow market = M15 ATR / price < 0.13%.

Because earlier breakeven exits free the one-active-trade slot, this was replayed sequentially rather than deleting/editing baseline trades post hoc.

| Year | Trades | Wins | BE exits | Expectancy |
|---:|---:|---:|---:|---:|
| 2017* | 77 | 9 | 36 | -0.065R |
| 2018 | 100 | 15 | 54 | **+0.140R** |
| 2019 | 84 | 21 | 38 | **+0.452R** |
| 2020 | 68 | 10 | 20 | -0.118R |
| 2021 | 81 | 10 | 42 | **+0.012R** |
| 2022 | 76 | 12 | 31 | **+0.039R** |
| 2023 | 76 | 10 | 38 | **+0.026R** |
| 2024 | 83 | 17 | 28 | **+0.157R** |
| 2025 | 101 | 30 | 32 | **+0.505R** |
| 2026 YTD | 69 | 30 | 0 | **+0.739R** |

Aggregate:

2017-2023:
- baseline: 540 trades, -0.015R expectancy, 93.26% max DD
- pace-BE: 562 trades, **+0.080R expectancy**, **70.73% max DD**
- frequency rises slightly from ~6.50 to ~6.76 trades/30d

2024-2026:
- baseline: +0.623R expectancy, 35.50% max DD
- pace-BE: **+0.455R expectancy**, **34.93% max DD**
- frequency ~7.65 trades/30d

This is the first research direction in this session that:
- makes both 2018 and 2022 positive
- materially reduces the 2017-2023 drawdown
- keeps the 2024-2026 block strongly positive
- preserves recent frequency close to the user's ~8/month preference

However, 2020 becomes worse and the 0.13% threshold was identified using this dataset. It therefore requires walk-forward validation before any deployment.

### Sequential replay — threshold 0.10%

A stricter definition of "slow":

2017-2023:
- +0.063R expectancy
- 74.02% max DD
- ~6.69 trades/30d

2024-2026:
- +0.480R expectancy
- 41.27% max DD
- ~7.56 trades/30d

It repairs 2018, makes 2020 breakeven and improves 2021/2023, but 2022 remains negative.

The 0.13% candidate is therefore more interesting, but not yet validated.

## Research conclusion

Today's data does not support another broad entry filter as the next priority.

The strongest new hypothesis is:

> RR10 should be allowed to enter normally, but trade protection may need to adapt to market speed.

In slow M15 volatility regimes, many trades make a useful initial move and then give it all back. Early breakeven protection can reduce this historical failure mode.

In faster modern regimes, the same early breakeven rule destroys too much expectancy, so the protection must be conditional rather than universal.

### Next validation

Before deployment:
1. Walk-forward the ATR%-threshold selection by year.
2. Test nearby thresholds rather than a single optimized 0.13%.
3. Validate that 2020 can be improved without losing the 2018/2022 repair.
4. Only after that combine with any adaptive TP research.

No TradingView Pine, cBot, canonical Python RR10 engine or live RR10 configuration was modified.
