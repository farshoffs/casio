# Fresh XAUUSD Research — M15 Conversions + New 3R MTF Candidate

## Scope

This research is independent of RR10.

Data:
- FxPro XAUUSD M15: 229,303 bars, 2017-01-02 -> 2026-09-18
- FxPro XAUUSD M5: 687,746 bars, 2017-01-02 -> 2026-09-18
- H1/H4 context resampled from the supplied FxPro history using completed bars only
- scoring begins 2017-03-04 after warm-up

Common assumptions:
- RM100 reset at the start of each calendar year
- 5% of current equity risked per entry
- one active trade
- stop-first if stop and target collide on the same execution bar
- gross results before spread, commission and slippage

## Requested conversion 1 — Tick-Volume Momentum Continuation on M15

M15 entry logic:
- completed H1 EMA20/EMA50 trend defines direction
- M15 tick-volume z-score >= 2.0 using a 50-bar normalization
- M15 candle body >=55% of range
- M15 range >=0.8 ATR14
- close location >=70% for longs / <=30% for shorts
- close breaks the previous 10 M15 highs/lows
- initial stop beyond the M15 impulse candle by 0.10 ATR

### Fixed 2R

Aggregate:
- 1,245 trades
- 37.35% WR
- +0.120R expectancy
- PF 1.19
- 10.87 trades/month average
- minimum completed month: 5
- 9/10 profitable calendar years
- worst annual ending equity: RM81.66
- worst annual max DD: 66.18%

### Fixed 3R

Aggregate:
- 1,120 trades
- 29.82% WR
- +0.193R expectancy
- PF 1.27
- 9.76 trades/month average
- minimum completed month: 3
- 8/10 profitable calendar years
- worst annual ending equity: RM71.16
- worst annual max DD: 79.35%

Year-by-year fixed 3R:
- 2017: RM660.89, +0.465R, DD 32.11%
- 2018: RM71.16, +0.022R arithmetic expectancy, DD 73.31%
- 2019: RM106.31, +0.085R, DD 66.59%
- 2020: RM532.75, +0.333R, DD 47.00%
- 2021: RM87.82, +0.051R arithmetic expectancy, DD 79.35%
- 2022: RM109.35, +0.091R, DD 64.84%
- 2023: RM168.67, +0.174R, DD 41.79%
- 2024: RM137.39, +0.133R, DD 66.89%
- 2025: RM692.08, +0.426R, DD 45.48%
- 2026 YTD: RM141.52, +0.188R, DD 31.15%

Interpretation:
- M15 conversion improves the raw expectancy substantially versus the original M5 screen.
- 3R has the stronger expectancy.
- raw fixed-target risk sequencing is still too severe.

## Requested conversion 2 — ADX/DI Momentum Rotation on M15

M15 entry logic:
- completed H1 EMA trend
- H1 ADX >=22
- H1 +DI/-DI agrees with direction
- completed H4 EMA trend agrees
- M15 EMA9/EMA20 cross back into HTF direction
- M15 RSI14 avoids the extreme zone
- stop beyond previous 10-bar M15 swing plus 0.10 ATR

### Fixed 2R
- 878 trades
- 33.49% WR
- +0.005R expectancy
- PF 1.01
- 7.66 trades/month
- 4/10 profitable years
- worst annual max DD 73.63%

### Fixed 3R
- 805 trades
- 24.72% WR
- -0.011R expectancy
- PF 0.99
- 7.02 trades/month
- 3/10 profitable years
- worst annual max DD 83.42%

Verdict:
**Reject the M15 ADX/DI conversion.**
Changing this strategy from M5 execution to M15 removes the small edge it previously had.

## New candidate — Tiered Relative-Volume Breakout 3R

This candidate was found while broadening the MTF search.

It does not reuse RR10.

### Timeframes
- M15 = signal/setup
- completed H1 = primary trend context
- completed H4 = secondary quality context
- genuine M5 = post-entry execution/management

### M15 setup

Direction:
- H1 EMA20 > EMA50 and H1 close > EMA20 for long
- mirror for short

M15 impulse:
- candle body >=55% of candle range
- candle range >=0.8 M15 ATR14
- close is in the upper 30% / lower 30% of the candle
- close breaks the previous 10 M15 highs/lows

### Tiered relative-volume rule

**Strong participation**
- M15 tick-volume z-score >=2.0
- trade directly when the setup is valid

**Moderate participation**
- tick-volume z-score from 1.25 up to <2.0
- require either:
  - completed H4 trend aligned with the trade, OR
  - completed H1 ADX >=25

This lets strong-volume breakouts trade without excessive filtering while demanding additional MTF evidence for moderate-volume breakouts.

### Initial risk and target

- Entry: M15 confirmation close
- Initial SL: M15 impulse extreme +/- 0.10 ATR14
- TP: fixed **3R**
- Risk: 5% current equity

### M5 protection

M5 does not create the signal.

After entry:
- if price reaches +0.5R
- move stop to breakeven starting from the **next M5 bar**
- no same-bar lookahead
- 3R target remains unchanged

This is still a 1:3 target architecture, but the outcome distribution contains many protected breakeven exits.

## Tiered 3R results

Aggregate:
- **2,028 trades**
- full 3R win rate: 14.20%
- breakeven exits: 53.90%
- expectancy: **+0.107R/trade**
- profit factor on realized wins/losses: **1.34**
- **17.66 trades/month average**
- **minimum completed month: 9**
- **100% of completed months have >=8 trades**
- **10/10 calendar years finish above RM100**
- worst annual ending balance: **RM108.38**
- worst annual max drawdown: **53.25%**

### Year by year — RM100 reset annually

| Year | Trades | Full 3R WR | BE exits | Expectancy | PF | RM100 -> | Max DD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 186 | 13.44% | 57.53% | +0.113R | 1.39 | RM206.31 | 48.20% |
| 2018 | 221 | 13.12% | 58.82% | +0.113R | 1.40 | RM239.39 | 39.05% |
| 2019 | 206 | 14.56% | 47.09% | +0.053R | 1.14 | RM115.11 | 45.48% |
| 2020 | 225 | 16.44% | 48.44% | +0.142R | 1.41 | RM306.19 | 40.13% |
| 2021 | 202 | 13.86% | 58.91% | +0.144R | 1.53 | RM298.08 | 41.57% |
| 2022 | 210 | 12.86% | 52.86% | +0.043R | 1.13 | **RM108.38** | 49.19% |
| 2023 | 196 | 15.82% | 50.51% | +0.138R | 1.41 | RM257.86 | 37.86% |
| 2024 | 227 | 12.33% | 55.95% | +0.053R | 1.17 | RM124.63 | **53.25%** |
| 2025 | 237 | 14.77% | 55.27% | +0.143R | 1.48 | RM348.98 | 37.86% |
| 2026 YTD | 118 | 15.25% | 53.39% | +0.144R | 1.46 | RM185.50 | 28.54% |

## Nearby-parameter robustness

The result is not dependent on one exact volume threshold.

Examples using the same 3R + M5 +0.5R protection:

- z>=1.0: 22.0 trades/month, min 10/month, 8/10 profitable years, DD ~62.5%
- z>=1.25 raw threshold: 19.1 trades/month, min 9/month, 9/10 profitable years, DD ~58.6%
- z>=1.5: 16.4 trades/month, min 7/month, 9/10 profitable years, DD ~61.6%
- z>=2.0: 11.3 trades/month, min 4/month, **10/10 profitable years**, DD ~48.9%

The tiered rule combines the frequency of the lower-volume threshold with stronger context on moderate-volume setups.

## Additional families screened at 3R

Also tested:
- H1/H4 volume Donchian breakouts
- MTF EMA wick/reclaim
- H1/H4 RSI2 pullback
- MTF MACD rotation
- volatility-compression breakout
- previous-day breakout continuation
- inside-bar continuation
- exhaustion snapback
- trend + exhaustion dual-regime system
- trend + wick-reclaim dual-module system

Several had positive aggregate expectancy, but none matched the tiered relative-volume candidate on the combined requirement of:
- >=8 trades in **every** completed month
- 3R target
- every year above RM100
- materially lower drawdown than the raw high-frequency systems

## Important limitation

The Tiered Relative-Volume candidate is **not ready for deployment yet**.

Reasons:
1. Results are gross before FxPro spread, commission and slippage.
2. More than half of trades exit at nominal breakeven. Real-world costs will turn many of those into small losses, so cost sensitivity is critical.
3. The rule family was discovered using the full historical sample. A strict walk-forward / holdout validation is still required.
4. 53% worst annual DD is materially better than the 80-99% screens, but is still substantial at 5% risk.

Next validation should:
- model realistic FxPro execution costs
- use rolling walk-forward parameter selection
- freeze 2024-2026 as a cleaner holdout where possible
- test whether +0.5R breakeven can be replaced by a small locked-profit stop that remains robust after costs

No RR10 code or live strategy was modified.
