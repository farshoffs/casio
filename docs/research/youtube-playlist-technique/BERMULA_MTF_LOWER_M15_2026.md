# Bermula One-MTF-Lower Backtest — 2026 YTD

Updated: 2026-09-24

## Correction to the hierarchy

The earlier translation incorrectly used the H4 Bermula/S&R structure as the actual setup layer.

The corrected interpretation is:

```text
H4 Bermula / S&R structure
        -> DIRECTION ONLY
        -> M15 Bermula / S&R setup
        -> M15 breakout
        -> M15 pullback / role reversal
        -> M1 confirmation
        -> M15 structural stop
        -> fixed-R exit study
```

This is closer to the supplied Paul-X lessons: the same Bermula logic can be used on the higher timeframe to establish direction, while the actual pattern is searched for on a lower timeframe.

## Data

- Instrument: XAUUSD
- Source: user-supplied FxPro M1 CSV
- File SHA256: `1054af491d4f6537270c7d88669556131109355674033c8881b5c82806ac1b82`
- Full history: 2017-01-02 23:00 UTC to 2026-09-24 00:21 UTC
- Test entries: 2026 only
- 2026 coverage is YTD through 2026-09-24
- Full history before 2026 is used only to establish causal H4/M15 context
- No session restriction
- No CASIO account-risk rules
- No fixed RR imposed before the sweep

## H4 direction

H4 direction is now determined with Bermula/S&R logic rather than generic HH/HL alone.

1. Identify a confirmed H4 Bermula origin:
   - H4 pivot;
   - departure reaches >= 1.5 H4 ATR within 3 H4 bars;
   - origin is not available until those confirming bars have closed.
2. When a confirmed H4 resistance Bermula is strongly broken upward, direction becomes bullish.
3. When a confirmed H4 support Bermula is strongly broken downward, direction becomes bearish.
4. Direction state persists until an opposite qualified H4 Bermula break occurs.

2026 H4 state changes under this definition:
- 2026-04-08 -> bullish
- 2026-04-28 -> bearish
- 2026-05-07 -> bullish
- 2026-05-15 -> bearish
- 2026-07-22 -> bullish

The direction before the first 2026 change is carried causally from the final pre-2026 H4 state.

## M15 setup

The same Bermula logic is applied to M15 to find the actual setup.

Operational mapping:

- M15 Bermula origin: confirmed M15 pivot with >= 1.5 M15 ATR departure within 3 M15 bars.
- Zone: full M15 origin candle.
- First structural break of that zone is considered.
- Breakout body >= 0.8 M15 ATR.
- Close must exceed the zone by >= 0.05 M15 ATR.
- Breakout must agree with H4 Bermula direction.
- Pullback/retest window: 24 M15 bars = 6 hours.
- M1 confirmation must occur within 15 minutes after the retest.
- M1 confirmation: close beyond previous 5 M1 bars in the setup direction, with body >= 0.4 M1 ATR.
- For conservative ordering, the M1 touch bar itself cannot also be the confirmation bar.
- Stop: beyond the opposite side of the M15 Bermula zone + 0.10 M15 ATR.
- Duplicate setups with identical entry minute/direction are reduced to the tighter local M15 structure.
- Realistic portfolio results use one open position at a time.

These numeric thresholds are deterministic research translations, not claims that Paul-X stated these exact numbers.

## Funnel

2026:

| Stage | Count |
|---|---:|
| H4-direction-aligned strong M15 breakout candidates | 158 |
| Reached M15 pullback/retest | 132 |
| M1 confirmations | 74 |
| Unique confirmed setups after exact-minute deduplication | **72** |

This is the main structural correction.

The previous H4-as-setup implementation produced only about 10 confirmed setups. Moving the pattern to M15 while reserving H4 for direction increases the 2026 opportunity set dramatically.

## How far the corrected setups travelled

Using the M15 structural stop as 1R and tracing price until that stop:

- setups traced: 72
- minimum MFE: **0.024R**
- 25th percentile: **0.443R**
- median MFE: **1.219R**
- 75th percentile: **3.196R**
- mean MFE: **7.121R**
- maximum observed MFE: **98.37R**

The mean is distorted upward by several very large trends, so the median/percentiles are more useful.

Target reach before structural SL:

| R target | Setups reaching it |
|---:|---:|
| 0.5R | 53 / 72 |
| 0.8R | 47 / 72 |
| 1.0R | 42 / 72 |
| 1.5R | 32 / 72 |
| 2.0R | 27 / 72 |
| 3.0R | 20 / 72 |
| 5.0R | 14 / 72 |
| 7.5R | 11 / 72 |
| 9.0R | 10 / 72 |
| 9.2R | 10 / 72 |
| 10R | 9 / 72 |

This is radically different from the H4-stop version, whose median excursion was only about 0.51R.

## One-position-at-a-time fixed-R backtest

Primary execution model: one live trade at a time. Later signals are skipped until the current trade closes.

| RR | Trades | Wins | Losses | WR | Net R | Exp/trade | PF | Max DD | 1bp sensitivity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5R | 70 | 52 | 18 | 74.29% | +8.0R | +0.114R | 1.44 | 3.5R | +6.11R |
| **0.8R** | **69** | **45** | **24** | **65.22%** | **+12.0R** | **+0.174R** | **1.50** | **3.8R** | **+10.14R** |
| 1.0R | 69 | 40 | 29 | 57.97% | +11.0R | +0.159R | 1.38 | 6.0R | +9.14R |
| 1.5R | 69 | 31 | 38 | 44.93% | +8.5R | +0.123R | 1.22 | 6.0R | +6.64R |
| **2.0R** | **63** | **25** | **38** | **39.68%** | **+12.0R** | **+0.190R** | **1.32** | **9.0R** | **+10.35R** |
| 3.0R | 57 | 17 | 40 | 29.82% | +11.0R | +0.193R | 1.28 | 10.0R | +9.50R |
| 4.0R | 54 | 11 | 43 | 20.37% | +1.0R | +0.019R | 1.02 | 14.0R | -0.42R |
| 5.0R | 51 | 10 | 41 | 19.61% | +9.0R | +0.176R | 1.22 | 14.0R | +7.67R |
| **5.4R** | **50** | **10** | **40** | **20.00%** | **+14.0R** | **+0.280R** | **1.35** | **14.0R** | **+12.69R** |
| 7.5R | 47 | 6 | 41 | 12.77% | +4.0R | +0.085R | 1.10 | 15.0R | +2.78R |
| 9.0R | 53 | 6 | 47 | 11.32% | +7.0R | +0.132R | 1.15 | 14.0R | +5.54R |
| 9.2R | 53 | 6 | 47 | 11.32% | +8.2R | +0.155R | 1.17 | 14.0R | +6.74R |

The 1 bp column is only a sensitivity because the source file does not contain bid/ask spread data.

## What is actually strongest in this 2026 sample?

Two different questions have different answers.

### Highest raw in-sample net R

The fine 0.1R sweep peaks at approximately **5.4R**, producing +14R gross.

But:
- WR is only 20%;
- max drawdown is 14R;
- longest loss streak is 14;
- 5.4R is selected after inspecting this same 2026 sample.

It is therefore an in-sample maximum, not something that should automatically be treated as the final exit rule.

### Smoother / more practical region

The lower-R plateau is much more stable:

- 0.8R: +12R, 65.2% WR, 3.8R DD;
- 1.0R: +11R, 58.0% WR, 6R DD;
- 2.0R: +12R, 39.7% WR, 9R DD;
- 3.0R: +11R, 29.8% WR, 10R DD.

The important result is that **0.8R through 3R all remain profitable in the baseline**, rather than profitability existing at only one exact optimized number.

## Monthly — 0.8R baseline

| Month | Trades | WR | Gross R | 1bp R |
|---|---:|---:|---:|---:|
| Jan | 7 | 57.1% | +0.2 | -0.05 |
| Feb | 3 | 66.7% | +0.6 | +0.55 |
| Mar | 14 | 78.6% | +5.8 | +5.51 |
| Apr | 6 | 66.7% | +1.2 | +0.96 |
| May | 5 | 40.0% | -1.4 | -1.53 |
| Jun | 10 | 90.0% | +6.2 | +5.96 |
| Jul | 6 | 50.0% | -0.6 | -0.75 |
| Aug | 16 | 56.3% | +0.2 | -0.27 |
| Sep* | 2 | 50.0% | -0.2 | -0.24 |

*September is incomplete through 2026-09-24.

## Monthly — 1R

| Month | Trades | WR | Gross R |
|---|---:|---:|---:|
| Jan | 7 | 42.9% | -1 |
| Feb | 3 | 66.7% | +1 |
| Mar | 14 | 64.3% | +4 |
| Apr | 6 | 33.3% | -2 |
| May | 5 | 40.0% | -1 |
| Jun | 10 | 90.0% | +8 |
| Jul | 6 | 50.0% | 0 |
| Aug | 16 | 56.3% | +2 |
| Sep* | 2 | 50.0% | 0 |

## Monthly — 2R

| Month | Trades | WR | Gross R |
|---|---:|---:|---:|
| Jan | 7 | 14.3% | -4 |
| Feb | 3 | 33.3% | 0 |
| Mar | 14 | 50.0% | +7 |
| Apr | 6 | 16.7% | -3 |
| May | 5 | 40.0% | +1 |
| Jun | 10 | 60.0% | +8 |
| Jul | 6 | 50.0% | +3 |
| Aug | 10 | 40.0% | +2 |
| Sep* | 2 | 0% | -2 |

## Parameter sensitivity

The lower-TF structure is not dependent on one exact pullback timer.

Keeping the H4 direction + M15 setup hierarchy and testing bounded timing interpretations:

| Pullback window | M1 confirmation window | Unique setups | 0.8R net | 1R net | 2R net | 3R net |
|---:|---:|---:|---:|---:|---:|---:|
| 6h | 15m | 72 | +12.0R | +11R | +12R | +11R |
| 12h | 15m | 73 | +12.8R | +12R | +14R | +14R |
| 24h | 15m | 75 | +14.4R | +14R | +16R | +13R |
| 6h | 30m | 91 | +9.2R | +10R | +2R | +1R |
| 12h | 30m | 94 | +9.8R | +11R | +3R | +3R |
| 24h | 30m | 96 | +11.4R | +13R | +5R | +2R |

This suggests the 0.8R–1R region is relatively stable even when the confirmation/pullback timing interpretation is changed. Larger targets are more sensitive to how loose the M1 confirmation window becomes.

## Rejected sensitivity — ultra-strict fresh zone

A separate test interpreted “fresh” as:

> after a M15 Bermula zone becomes known, its first-ever revisit must itself be the breakout.

That interpretation produced only:
- 16 breakout events,
- 8 confirmed trades.

Results:
- 0.8R: 5/8 wins, +1R gross;
- 1R: 4/8, flat gross and negative after 1 bp;
- 2R: 1/8, -5R;
- 3R: 0/8, -8R.

This appears too restrictive to use as the main Bermula definition. It is retained as a sensitivity, not promoted to a creator rule.

## Interpretation

The user's correction materially improves the translation.

Treating H4 as **direction only** and moving the actual Bermula pattern to M15:

- increases setup frequency;
- gives much tighter structural stops;
- changes median MFE from roughly 0.51R to **1.22R**;
- creates a broad profitable RR region instead of a structurally negative payoff profile;
- produces dozens of 2026 trades rather than only a handful.

This is the first version of the Bermula translation whose 2026 M1 behavior looks like a viable mechanical system rather than a mis-scaled higher-timeframe implementation.

## Next research step

Do not optimize dozens of entry thresholds.

The next clean test should keep this hierarchy fixed and validate it on:
1. prior years from the same FxPro M1 file, year-by-year;
2. an untouched holdout slice;
3. then compare a small set of predeclared exits such as 0.8R, 1R, 2R, 3R and the high-R 5.4R research candidate.

That will tell us whether the 2026 edge is persistent or merely fitted to one year.
