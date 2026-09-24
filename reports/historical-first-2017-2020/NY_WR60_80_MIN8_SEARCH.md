# CASIO NY WR 60–80 / Minimum 8 Per Month Search — 2017–2020

## Current hard rules

- Start RM100.
- Risk 5% of current equity per trade.
- Fixed RR 1:3.
- Real structural SL only.
- No breakeven / protected SL / partial-win accounting.
- New York session only, DST-aware using America/New_York.
- Target WR 60%–80%.
- No hard DD rejection threshold, but DD remains a reported risk metric.
- Minimum 8 completed trades in every calendar month.
- One position at a time.
- Conservative same-M1-bar ambiguity: SL first.
- 1 bp round-trip cost.
- Development data only: user-supplied FxPro XAUUSD M1, 2017-01-01 through 2020-12-31.
- 2021+ remains sealed.

MTF is not a hard requirement in this rule set. M1-native, M5+M1, M15+M1 and MTF systems were all allowed to compete.

## Data

- 1,411,461 M1 bars in the 2017–2020 development slice.
- M5/M15/H1/H4, when used, were derived from the same FxPro M1 feed.

# Strict pass count

**0**

No technique tested so far has simultaneously achieved:
- WR >=60% and <=80%;
- fixed 3R;
- real SL;
- >=8 completed trades in every one of the 48 months;
- New York-only execution.

## Current strict-frequency frontier

The best configuration found so far that genuinely meets the minimum-eight-trades rule in all 48 months is a time-specialized M5 deep-retracement system:

### M5 impulse -> 93% retracement, NY 08:30–10:30

Representative rules:
- NY-local window 08:30–10:30.
- M5 directional impulse.
- M5 body >=0.5 ATR.
- Body/range >=0.50.
- Tick-volume ratio >=1.0.
- Break prior 3 M5 bars.
- ADX >=22.
- Pending entry at 93% retracement of the completed M5 signal range.
- Pending validity 15 minutes.
- Real SL beyond the completed M5 signal wick +0.05 ATR.
- Fixed 3R.
- M1 exact fill and SL/TP sequencing.

Results:
- 892 trades.
- WR **40.13%**.
- Minimum trades/month **10**.
- Average trades/month 18.58.
- 48/48 months >=8 trades.
- Expectancy -0.279R/trade after cost.
- PF 0.754.
- Fails the 60% WR target decisively.

This remains the best WR observed among configurations that truly satisfy the eight-trades-every-month condition.

# Technique families tested under the new WR 60–80 rule

## 1. M1 ultra-deep displacement continuation

Retracements:
- 90%;
- 93%;
- 95%;
- 97%.

Best frequency-valid WR:
- **28.07%**.
- 3,092 trades.
- Minimum 45 trades/month.
- Negative expectancy.
- Rejected.

Key finding: ultra-tight risk after M1 ultra-deep entry makes the 1 bp transaction cost very large in R terms.

## 2. M1 liquidity sweep / failed-break rejection -> deep retracement

5,544 configurations.

Best frequency-valid:
- 1,105 trades.
- WR **32.40%**.
- Minimum 16/month.
- Negative expectancy.
- Rejected.

## 3. New York key-level techniques

Levels tested:
- overnight high/low;
- London high/low;
- premarket range;
- OR15;
- OR30;
- previous-NY high/low.

Both continuation and sweep/reversal logic were tested.

Best frequency-valid:
- OR15 sweep/reversal.
- 549 trades.
- WR **38.43%**.
- Minimum exactly 8/month.
- Negative expectancy.
- Rejected.

## 4. M1 exhaustion / mean reversion

Families:
- RSI2 extreme/reclaim;
- Bollinger / z-score extreme;
- engulfing after extreme;
- completed-M5 range/counter-trend contexts.

Best frequency-valid:
- 1,068 trades.
- WR **34.27%**.
- Minimum 12/month.
- Negative expectancy.
- Rejected.

## 5. Scheduled NY opening impulse

Anchors:
- 08:20 ET COMEX lead-in;
- 08:30 macro window;
- 09:30 cash open;
- 10:00 follow-through.

3/5/10/15-minute impulse ranges with deep retracement were tested.

Best WR roughly 35%; filled-trade monthly coverage also failed for the better-quality variants.

Rejected.

## 6. M5 ultra-deep impulse -> retracement

1,536 focused configurations.

Best frequency-valid:
- 1,718 trades.
- WR **35.97%**.
- Minimum 20/month.
- Negative expectancy.
- Rejected.

## 7. M5 time-of-day specialization

11,796 configurations across rolling 60/120/180-minute NY windows.

Best frequency-valid is the current frontier:
- 08:30–10:30 ET.
- 892 trades.
- WR **40.13%**.
- Minimum 10/month.
- Negative expectancy.

No strict pass.

## 8. M15 impulse -> ultra-deep retracement

9,630 configurations.

Best frequency-valid:
- 880 trades.
- WR **35.91%**.
- Minimum 11/month.
- Negative expectancy.
- Rejected.

## 9. Two-stage M5 impulse -> deep touch -> M1 reversal confirmation

13,824 configurations.

M1 confirmations:
- level reclaim;
- engulfing;
- MSS3;
- two consecutive directional bars.

Best frequency-valid:
- 1,007 trades.
- WR **28.60%**.
- Minimum 11/month.
- Negative expectancy.

Waiting for an M1 reversal after the M5 deep touch did not rescue the dense setup.

## 10. Causal outcome-model stress test

Causal features only:
- M1 momentum/RSI/z-score/wicks/EMA distance/volume;
- completed M5/H1 ADX/DI/EMA;
- time-of-day;
- volatility state.

Training:
- 2017 + first half 2018.

Validation:
- second half 2018.

Frozen test:
- 2019–2020.

Validation/test AUC:
- approximately **0.50–0.51**.

At thresholds dense enough for >=8 trades/month:
- test WR stayed around **27%**.

Rejected. There was no useful hidden predictive separation in this candidate pool.

## 11. Anchored New York VWAP deviation -> reclaim/reversion

Session VWAP was anchored from 08:00 New York time with cumulative tick-volume weighting.

Tested:
- 1.5 / 2.0 / 2.5 sigma deviations;
- touch/reclaim;
- close-cross reclaim;
- RSI2 extreme + reclaim;
- optional completed-M5 range context;
- real recent-swing stops.

60 focused exact-replay configurations after frequency pre-screening.

Strict passes: 0.

Best frequency-valid:
- 4,083 trades.
- WR **26.06%**.
- Minimum 52/month.
- Expectancy -0.154R.
- PF 0.826.

VWAP reversion is rejected for this target.

## 12. London/premarket directional handoff -> NY pullback

New family:
- measure completed 03:00–08:30 NY-local premarket direction and close-location;
- trade only in the premarket direction during 08:30–12:30 or 09:30–12:30;
- M5 EMA20/EMA50 pullback or RSI2 reclaim;
- optional M5 ADX/body filtering;
- M1 execution;
- structural M5 swing SL;
- fixed 3R.

2,448 exact-replay configurations after frequency pre-screening.

Strict passes: 0.

Best frequency-valid:
- 1,325 trades.
- WR **27.62%**.
- Minimum 10/month.
- Expectancy -0.032R.
- PF 0.961.

Directional handoff did not produce the required high-WR edge.

# High-WR frontier

60–80% WR configurations do exist in the data, but they are ultra-selective.

Examples already found in earlier M1 research:
- NY opening-hour MTF displacement variants around 60–72% WR;
- some 88.6% deep-retracement variants around 70%+ WR;
- CASIO NY Precision v1: 61.54% WR, 26 trades total.

The problem is not finding isolated 60%+ setups. The problem is obtaining at least eight **independent completed trades in every month** while retaining that win rate.

The high-WR setups generally produce only about 10–30 trades across the entire four-year development sample, versus a theoretical minimum of 384 trades required by 8 x 48 months.

## Portfolio arithmetic

Sparse high-WR setups cannot mathematically rescue hundreds of lower-WR filler trades.

For example, suppose:
- 30 elite trades win at 70%;
- the portfolio must contain at least 384 trades;
- target total WR is 60%.

The remaining 354 trades would still need approximately **59.15% WR** themselves.

Therefore combining a few sparse 70% setups with the existing 30–40% dense systems cannot satisfy the target. The missing component must itself be a genuinely frequent ~60% edge.

# Current conclusion

The current search has now covered:

- continuation;
- breakout;
- deep retracement;
- ultra-deep retracement;
- two-stage confirmation;
- liquidity sweep / failed break;
- key-level reactions;
- opening range;
- scheduled opening impulses;
- exhaustion / mean reversion;
- RSI/Bollinger extremes;
- M1/M5/M15 impulse structures;
- time-of-day specialization;
- anchored VWAP reversion;
- premarket directional handoff;
- MTF filters;
- M1-native execution;
- causal machine-learning selection.

No honest strict pass has been found.

The best true minimum-8-per-month WR remains **40.13%**, far below the requested 60% floor.

No protected stop, BE conversion, partial-win accounting, future-data tuning or 2021+ data was used.

2021–2026 remains sealed.


# Additional technique checks

## 13. NY cash-open gap reversal / continuation

Daily structure:
- previous completed NY cash-session close;
- current 09:30 New York cash open;
- first 1/3/5/10/15 minute opening impulse;
- gap-fade and gap-continuation modes;
- real stop beyond the completed opening extreme plus ATR buffer;
- M1 execution;
- fixed 3R.

Only the loose five-minute gap-fade configuration maintained at least eight completed trades in every month.

Best frequency-valid result:
- 516 trades.
- WR **26.74%**.
- Minimum trades/month **8**.
- Average 10.75/month.
- 48/48 months >=8.
- Expectancy -0.082R.
- PF 0.902.

Strict passes: 0.

This daily-frequency technique is rejected.

## Updated frontier after VWAP, premarket handoff and NY gap tests

| Technique | Best WR with min >=8 every month |
|---|---:|
| M5 time-window deep retracement, 08:30–10:30 | **40.13%** |
| OR15/key-level sweep | 38.43% |
| M5 ultra-deep retracement | 35.97% |
| M15 ultra-deep retracement | 35.91% |
| M1 exhaustion / mean reversion | 34.27% |
| M1 liquidity sweep + deep entry | 32.40% |
| Two-stage M5 touch -> M1 confirmation | 28.60% |
| M1 ultra-deep displacement | 28.07% |
| Premarket directional handoff | 27.62% |
| NY cash-open gap fade | 26.74% |
| Anchored NY VWAP reclaim/reversion | 26.06% |

The strict-frequency frontier therefore remains **40.13% WR**, with no configuration reaching the requested 60% floor.
