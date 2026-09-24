# CASIO MTF Strict Search — New York Only, 2017–2020

## Current hard rules

All techniques in this research obeyed the following framework:

- Start equity: RM100.
- Risk: 5% of current equity per entry.
- Fixed RR: 1:3.
- Real structural SL only.
- No breakeven / protected SL.
- New York session only.
- DST-aware using `America/New_York`.
- MTF is mandatory for every technique:
  - completed H1/H4 context,
  - M5 setup/state,
  - M1 execution/confirmation or M1-native entry under completed M5 + H1/H4 state.
- WR target: >=50%. A result above 60% is treated as exceeding the target, not as a failure.
- Max DD: <25%.
- Minimum trades: >=8 in **every calendar month**.
- M1 same-bar SL/TP ambiguity: SL first.
- One open position at a time.
- 1 bp round-trip cost.
- Development data: FxPro XAUUSD M1, 2017-01-02 through 2020-12-31 only.
- 2021+ remains sealed.

For continuity with prior research, 4/4 profitable years was also tracked as an additional safeguard. It did not affect the main conclusion because no configuration passed the frequency + DD + WR requirements.

## Search coverage

### M5-led MTF catalog
- 26 technique families.
- 1,552 unique MTF setup logics.
- 4,616 entry/configuration variants fully replayed on M1.
- Strict passes: 0.

Families:
ADX/DI rotation, tick-volume breakout, Donchian, EMA20 pullback, EMA50 pullback, RSI8 reclaim, RSI2 snapback, MACD rotation, Bollinger squeeze, displacement, FVG trend, inside-bar breakout, NR breakout, VWAP reclaim, ORB breakout, ORB retest, overnight breakout, overnight retest, previous-NY sweep, overnight sweep, premarket sweep, rolling sweep, failed breakout, VWAP fade, Bollinger fade, volatility-shock reversal.

### NY sub-session displacement search
- Pre-open, opening hour, mid-morning, lunch, afternoon and late NY windows.
- 960 variants fully replayed.
- Strict passes: 0.

### M1-native MTF catalog
- 12 M1-native families.
- 1,800 entry variants considered.
- 443 variants had raw signal frequency sufficient to potentially satisfy >=8 every month and were fully replayed.
- Strict passes: 0.

Families:
M1 EMA20 reclaim, EMA50 reclaim, RSI2 reclaim, RSI8 reclaim, micro breakout, M1 displacement, sweep continuation, FVG continuation, engulfing continuation, inside-bar breakout, Bollinger squeeze, pullback-break continuation.

### M1 ultra-deep-entry search
- 1,560 fully replayed variants.
- Retracement entries: 78.6%, 83.6%, 88.6%, 90%, 93%.
- Wait windows: 5, 10, 20 minutes.
- Strict passes: 0.

### Event-based NY MTF techniques
Core daily-event tests included:
- OR break/retest,
- overnight break/retest,
- previous-NY break/retest,
- VWAP pullback after opening extension,
- opening-drive pullback,
- 10AM continuation,
- OR sweep/rejoin.

The core event rules failed the >=8-every-month raw-signal requirement before execution, so replay could not improve their frequency.

## Total coverage

- Approximately **8,950** parameter/entry variants considered.
- Approximately **7,579** variants fully replayed at M1 resolution.
- 35 core technique families plus NY sub-session and event-based variants.
- **Strict passes: 0.**

# Critical frontier

## Best precision candidate

`DISPLACEMENT__H4_H1ADX__NY_CASH_AM__r705__adx30__bf0.75__body0.5__lb16__vol1.15`

- Trades: 24
- WR: **58.33%**
- Expectancy: **+1.131R**
- PF: **3.22**
- DD: **22.52%**
- Profitable years: **4/4**
- Minimum monthly trades: **0**

This satisfies the WR and DD targets, but fails the monthly-frequency requirement badly.

A nearby variant:

`DISPLACEMENT__ALIGN__NY_CASH_AM__r705__adx30__bf0.75__body0.5__lb16__vol1.15`

- Trades: 32
- WR: **53.13%**
- Expectancy: +0.923R
- PF: 2.62
- DD: **17.40%**
- Profitable years: 4/4
- Minimum monthly trades: 0.

## Best opening-hour precision result

`SUBDISP__H4_H1ADX__NY_OPEN60__r786__A28__V1.15__B0.6__F0.72__L16`

- Trades: 17
- WR: **58.82%**
- Expectancy: +1.083R
- PF: 3.05
- DD: **7.10%**
- Profitable years: 4/4
- Minimum monthly trades: 0.

Again, precision is excellent but frequency is far below the hard requirement.

# Frequency-qualified frontier

## M5-led systems

Among configurations that actually reached >=8 trades in every month, the highest WR was only:

`DONCHIAN__H4_H1ADX__NY_CASH__r705__adx16__bf0.5__body0.25__lb8`

- Trades: 887
- Minimum month: **10**
- WR: **28.64%**
- Expectancy: -0.301R
- PF: 0.71
- DD: ~100%.

No M5-led configuration with >=8 trades every month reached even 30% WR.

## M1-native systems

Among M1-native configurations with >=8 trades in every month, a representative top-WR result was:

`M1MTF__MICRO_BREAK__ALIGN_M5__NY_CASH__r705__adx20__bf0.7__body0.5__lb20__m5adx16__vol1.0`

- Trades: 910
- Minimum month: **8**
- WR: **29.89%**
- Expectancy: -0.525R
- PF: 0.57
- DD: ~100%.

## M1 ultra-deep entries

Deep M1 entries improved the high-frequency WR frontier, but not enough:

`DEEPM1__MICRO_BREAK__H1H4_M5DI__R0.886__W20__adx20__bf0.6__body0.3__lb10__m5adx16__vol1.0`

- Trades: 878
- Minimum month: **8**
- WR: **35.42%**
- Expectancy: -0.686R
- PF: 0.49
- DD: ~100%.

This was the highest meaningful WR found among the configurations satisfying >=8 trades in every calendar month, but it is still far below the 50% floor and is strongly unprofitable.

# Strongest negative result

Across the M5-led, M1-native and M1-deep batches:

**Number of configurations with both**
- minimum >=8 trades every month, and
- DD <25%

was:

**0**

This is true even before applying the WR >=50% rule.

Therefore the current bottleneck is not merely finding a better indicator. The combination of:
- 5% risk per entry,
- >=8 trades every month,
- fixed 3R,
- DD below 25%,

is already extremely restrictive on this 2017–2020 FxPro sample.

# Drawdown mathematics

At 5% current-equity risk, six consecutive full -1R losses from an equity peak produce:

`1 - 0.95^6 = 26.49%`

drawdown before trading costs.

Therefore any system that suffers a six-loss run from an equity peak already violates DD <25%.

The minimum-frequency rule implies at least:

`8 trades/month × 48 months = 384 trades`.

Under an illustrative independent-trade model, the probability of observing at least one six-loss streak in 384 trades is approximately:

- true WR 50%: **95.6%**
- true WR 55%: **83.3%**
- true WR 60%: **61.3%**
- true WR 65%: **36.7%**

Real trades are not independent, so these figures are not forecasts. They show why DD <25% at 5% risk is a severe sequence constraint even for a genuinely high-WR system.

# Current conclusion

No tested MTF technique complies with all current rules.

Two different frontiers exist:

1. **Precision frontier**
   - WR 50–59%
   - DD 7–23%
   - positive expectancy
   - 4/4 profitable years
   - but only roughly 0–1 trade/month on average and zero-trade months.

2. **Frequency frontier**
   - >=8 trades in every month
   - hundreds of trades
   - but WR roughly 25–35%
   - poor expectancy
   - catastrophic DD.

The search therefore should not loosen a single precision technique merely to manufacture frequency. Any next phase should look for a genuinely different **MTF regime router / independent setup portfolio** whose sleeves are individually high-quality and whose combined signal stream covers every month without introducing six-loss clusters.

2021+ remains sealed.
