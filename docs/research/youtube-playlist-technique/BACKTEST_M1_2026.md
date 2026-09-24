# Bermula M1 Backtest — 2026 YTD

Updated: 2026-09-24

## Scope

This report tests the Paul-X / Bermula continuation logic learned from the supplied playlist using the user's complete FxPro XAUUSD M1 dataset.

**Only entries in 2026 are counted.** The dataset currently ends at **2026-09-24 00:21 UTC**, so this is 2026 YTD, not a full-calendar-year result.

Historical data before 2026 is used only to establish causal H1/H4 S/R, Bermula origins and prior structural context. No future bars are used.

No CASIO user constraints were imposed:
- no RM100 starting balance,
- no 5% risk rule,
- no fixed 1:3,
- no New York-only filter,
- no target win-rate requirement,
- no minimum monthly trade count.

Results are expressed in R.

## Dataset

- File: `fxpro_xauusd_m1.csv`
- Instrument: XAUUSD
- Source label: FxPro
- Timeframe: M1
- Full source history starts: 2017-01-02 23:00 UTC
- 2026 data starts: 2026-01-01 23:00 UTC
- Current end: 2026-09-24 00:21 UTC
- 2026 M1 rows: 258,330
- Full file SHA256: `1054af491d4f6537270c7d88669556131109355674033c8881b5c82806ac1b82`

## Source-derived setup

The higher-confidence continuation family was used:

```text
H4 Bermula / SNR origin
  -> H4 direction/context
  -> H1 strong breakout
  -> pullback / role-reversal retest
  -> M1 lower-timeframe confirmation
  -> structural stop
  -> nearest known opposing S/R target
```

Directly source-supported concepts:
- support/resistance is the base map;
- Bermula is the origin area where meaningful rise/fall began;
- strong displacement matters;
- breakout -> pullback -> entry;
- entry requires lower-timeframe confirmation;
- broken S/R may reverse role;
- structural risk management;
- reversal and continuation are separate setup families.

The reversal family is not included because its exact deterministic trigger is still unresolved from the supplied source material.

## Operational definitions used

These are research translations, not claims that Paul-X stated the numeric values verbatim.

- H4 Bermula origin: confirmed H4 pivot with >= 1.5 H4 ATR departure within 3 H4 bars.
- Zone geometry: full H4 origin candle.
- H1 breakout: candle body >= 0.8 H1 ATR and close >= 0.05 H1 ATR beyond the zone.
- Pullback expiry: 24 hours.
- Retest tolerance: 0.05 H1 ATR.
- M1 confirmation: directional break of previous 5 M1 bars, body >= 0.4 M1 ATR.
- Confirmation window after touch: 60 minutes.
- SL: opposite side of the Bermula zone + 0.10 H1 ATR buffer.
- TP: nearest causally known opposing H1 or H4 structural S/R.
- Same M1 bar touching both SL and TP: resolve conservatively as SL.
- Primary results are gross R because the file has no bid/ask spread series.
- A 1 bp round-trip friction sensitivity is reported separately.

## Baseline A — strict H4 structural direction

Here “direction” is operationalized as H4 HH+HL for bullish or LH+LL for bearish.

### Funnel

- Strong 2026 zone-break events before direction filter: 11
- Rejected by strict H4 direction interpretation: 9
- Qualified breakout events: 2
- Pullbacks: 2
- M1 confirmations: 2
- Completed trades: 2

The H1 and H4 nearest structural targets happened to resolve to the same price for these two trades.

| Metric | Gross |
|---|---:|
| Trades | 2 |
| Wins / Losses | 2 / 0 |
| Win rate | 100.00% |
| Net R | +0.095R |
| Expectancy | +0.048R/trade |
| Average planned R:R | 0.048R |
| Median planned R:R | 0.048R |
| Max drawdown | 0.000R |

With a 1 bp friction sensitivity:
- effective wins/losses: 1 / 1;
- effective WR: 50.00%;
- net: +0.070R;
- expectancy: +0.035R/trade.

### Strict trades

| Entry UTC | Side | Entry | Stop | Structural target | Planned R:R | Gross result | 1bp sensitivity |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-05-05 09:01 | Short | 4555.15 | 4584.81 | 4554.87 | 0.009R | +0.009R | -0.006R |
| 2026-06-10 12:11 | Short | 4140.01 | 4181.26 | 4136.48 | 0.086R | +0.086R | +0.076R |

This sample is too small to estimate a stable win rate. More importantly, the native structural reward is extremely small relative to the stop.

## Sensitivity B — do not impose the HH/HL direction veto

Paul-X clearly teaches direction/bias, but the playlist does not establish that his exact deterministic rule is the strict HH/HL definition used above. Therefore this sensitivity keeps the same Bermula, breakout, pullback, M1 confirmation and structural stop rules, but does not reject a setup solely because the formal HH/HL state disagrees.

This is **not selected as a better strategy**. It exists to measure the impact of an unresolved translation choice.

### Funnel

- Strong breakout events: 11
- Pullback/retest reached: 10
- M1 confirmation reached: 10
- Completed trades: 10

### H4 structural exit

| Metric | Result |
|---|---:|
| Trades | 10 |
| Wins / Losses | 6 / 4 |
| Win rate | 60.00% |
| Net R | **-3.046R** |
| Expectancy | **-0.305R/trade** |
| Profit factor | **0.238** |
| Max drawdown | **3.768R** |
| Average planned R:R | 0.260R |
| Median planned R:R | 0.180R |
| Avg winning trade | +0.159R |
| Avg losing trade | -1.000R |
| Max win streak | 5 |
| Max loss streak | 2 |

Given the observed average winner of 0.159R versus a 1R loser, the approximate break-even win rate is **86.3%**.

With 1 bp friction:
- WR: 50.00%;
- net: -3.157R;
- expectancy: -0.316R/trade;
- PF: 0.218;
- max DD: 3.809R.

### H1 structural exit

| Metric | Result |
|---|---:|
| Trades | 10 |
| Wins / Losses | 8 / 2 |
| Win rate | **80.00%** |
| Net R | **-1.486R** |
| Expectancy | **-0.149R/trade** |
| Profit factor | **0.257** |
| Max drawdown | **1.694R** |
| Average planned R:R | 0.082R |
| Median planned R:R | 0.054R |
| Avg winning trade | +0.064R |
| Avg losing trade | -1.000R |
| Max win streak | 5 |
| Max loss streak | 1 |

With winners averaging only 0.064R against a 1R loss, the approximate break-even win rate is **94.0%**.

With 1 bp friction:
- WR: 60.00%;
- net: -1.597R;
- expectancy: -0.160R/trade;
- PF: 0.211;
- max DD: 1.735R.

## Month-by-month — relaxed direction, H1 exit

| Month | Trades | Gross wins | Gross WR | Gross R | 1bp R | Avg planned RR |
|---|---:|---:|---:|---:|---:|---:|
| 2026-01 | 1 | 0 | 0% | -1.000 | -1.006 | 0.237 |
| 2026-02 | 1 | 1 | 100% | +0.024 | +0.015 | 0.024 |
| 2026-03 | 1 | 1 | 100% | +0.041 | +0.033 | 0.041 |
| 2026-04 | 3 | 2 | 66.7% | -0.688 | -0.713 | 0.126 |
| 2026-05 | 1 | 1 | 100% | +0.009 | -0.006 | 0.009 |
| 2026-06 | 1 | 1 | 100% | +0.086 | +0.076 | 0.086 |
| 2026-07 | 1 | 1 | 100% | +0.021 | -0.002 | 0.021 |
| 2026-08 | 1 | 1 | 100% | +0.020 | +0.006 | 0.020 |
| 2026-09* | 0 | 0 | — | 0.000 | 0.000 | — |

*Data currently ends September 24.

## Trade list — relaxed direction, H1 exit

| Entry UTC | Side | Planned RR | Gross R |
|---|---|---:|---:|
| 2026-01-30 10:08 | Short | 0.237 | -1.000 |
| 2026-02-24 14:12 | Short | 0.024 | +0.024 |
| 2026-03-23 09:33 | Short | 0.041 | +0.041 |
| 2026-04-07 23:04 | Long | 0.240 | +0.240 |
| 2026-04-20 00:52 | Short | 0.067 | -1.000 |
| 2026-04-28 10:49 | Short | 0.072 | +0.072 |
| 2026-05-05 09:01 | Short | 0.009 | +0.009 |
| 2026-06-10 12:11 | Short | 0.086 | +0.086 |
| 2026-07-22 02:23 | Long | 0.021 | +0.021 |
| 2026-08-21 09:38 | Long | 0.020 | +0.020 |

## Interpretation

The important finding is **not win rate**.

The Bermula continuation sequence is detectable on the FxPro M1 data, and the relaxed-direction interpretation can show a high structural-target hit rate. But the nearest-S/R target interpretation creates very poor asymmetry: most winners are only a few hundredths of one R while a failed setup loses approximately 1R.

That is why:
- 80% gross WR with H1 exits still loses -1.486R;
- 60% gross WR with H4 exits loses -3.046R.

This means the unresolved **Paul-X exit weapon / target-selection rule is decisive**. Using “nearest historical S/R” literally is not enough to produce an economically attractive continuation system in 2026 YTD.

The strict direction interpretation is too sparse to judge and also produces very small reward distances.

## Conclusion

The 2026 M1 evidence supports the **setup sequence**:

```text
Bermula -> breakout -> pullback -> lower-TF confirmation
```

but does **not** support the current structural-exit translation as a complete profitable system.

The next research priority should be the creator-native exit logic and the proprietary confirmation/zone terminology rather than tuning the entry thresholds to manufacture a better result.
