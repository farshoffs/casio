# CASIO New MTF High-Frequency Edge Search — 2017–2020

## Hard rules

All tests in this batch used the user's current hard requirements:

- Start capital RM100.
- Risk 5% of current equity per trade.
- Fixed RR 1:3.
- Real structural SL only.
- No breakeven / protected SL.
- MTF required:
  - completed H1/H4 context;
  - M5 setup/context where applicable;
  - M1 execution or native M1 trigger.
- Session unrestricted: Asia, London, New York and full-day states allowed.
- WR floor 50% (target band 50–60%; >60% is not rejected).
- Max DD <25%.
- Minimum 8 completed trades in every calendar month.
- One position at a time.
- Conservative same-M1-bar ambiguity: SL first.
- 1 bp round-trip cost.
- Development data only: FxPro XAUUSD M1, 2017-01-01 through 2020-12-31.
- 2021+ remains sealed.

## Data

User-supplied FxPro M1 file was sliced to 2017–2020 only:

- 1,411,461 M1 bars.
- M5, H1 and H4 were derived from the same M1 feed to avoid cross-feed mismatch.

## New families tested

This batch deliberately avoided simply re-running the old NY grids. It tested new/high-frequency MTF structures:

1. Dense H1/H4-aligned M5 displacement with deep retracement.
2. H1/H4 trend pullback + M5 EMA20/EMA50 reclaim + RSI2 state + M1 micro confirmation.
3. H1/H4 trend liquidity sweep/reclaim + M1 confirmation.
4. Causal MTF state selector (machine-learning stress test).
5. Completed H1 impulse + H4 bias -> M5 retracement/reclaim -> M1 confirmation.
6. Tokyo/London/New York opening-range breakout/retest.
7. Tokyo/London/New York opening-range sweep/reclaim.
8. H4/H1 range-regime failed breakout / liquidity reversal.
9. Fully M1-native liquidity sweep/reclaim under completed H1/H4 + M5 context.
10. Fully M1-native displacement -> deep retracement under completed H1/H4 + M5 context.
11. BBMA-style MTF momentum -> reentry -> M1 execution.
12. Triple-timeframe H4 trend -> completed H1 pullback/reclaim -> M5 continuation -> M1 confirmation.

## Strict pass count

**0**

No tested strategy satisfied all of:

- WR >=50%;
- DD <25%;
- minimum 8 trades in every one of the 48 months;
- fixed 3R;
- real SL;
- 5% risk;
- MTF.

## Best new high-frequency frontier

### M1-native displacement -> 78.6% retracement

This was the strongest new family in the dense-frequency region.

Representative configuration:

- H4 trend + H1 DI/ADX context.
- Completed M5 close above/below EMA20.
- Completed M5 ADX >=18.
- M1 displacement breaks prior 3 M1 bars.
- M1 body >=0.9 M1 ATR.
- M1 body/range >=0.65.
- M1 tick-volume ratio >=1.2.
- Pending entry at 78.6% retracement of the M1 displacement candle.
- Pending validity 3 minutes.
- SL beyond the real M1 displacement wick + ATR buffer.
- TP fixed 3R.

Dense result:
- 1,233 trades.
- WR **40.06%**.
- Minimum month **8**.
- Average 25.69 trades/month.
- 48/48 months have at least 8 trades.
- Expectancy -0.044R after 1 bp cost.
- DD ~100%.
- Fails WR and DD.

The M1 deep-retracement family is materially better than the other frequency-valid families, but still far below the 50% floor and its loss clustering destroys the account at 5% risk.

### Selective M1 deep-displacement frontier

A stricter H4/H1 + completed-M5 configuration achieved:

- 347 trades.
- WR **47.55%**.
- +0.270R/trade.
- PF 1.31.
- 4/4 profitable calendar years.
- Average 7.23 trades/month.
- Minimum month **1**.
- DD **47.91%**.

This is the closest genuinely new technique to the quality/frequency target, but it still fails:
- WR <50%;
- DD >25%;
- minimum monthly frequency.

## Other frequency-valid families

### H1/H4 trend pullback + M1 confirmation

Best configuration that still maintained minimum 8 trades/month:

- 741 trades.
- WR 30.23%.
- Minimum month 8.
- DD 99.75%.

Rejected.

### Trend liquidity sweep/reclaim

Best frequency-valid configuration:

- 1,272 trades.
- WR 28.46%.
- Minimum month 9.
- DD ~100%.

Rejected.

### H4/H1 range-regime failed breakout

Best frequency-valid configuration:

- 1,558 trades.
- WR 27.15%.
- Minimum month 9.
- DD ~100%.

Rejected.

### M1-native liquidity sweep/reclaim

Best frequency-valid configuration:

- 1,785 trades.
- WR 27.45%.
- Minimum month 8.
- DD ~100%.

Rejected.

### BBMA-style MTF momentum -> reentry

Best frequency-valid configuration:

- 1,278 trades.
- WR 29.03%.
- Minimum month 11.
- DD ~100%.

Rejected.

## Opening-range research

Tokyo, London and New York opening-range breakout/retest and sweep/reclaim were tested with completed H1/H4 contexts and M1 execution.

The higher-quality variants were too sparse. London OR retest variants reached roughly mid-30% WR with only about 3–4 trades/month average. No OR family simultaneously approached 50% WR and the 8/month floor.

## H1 impulse / triple-timeframe pullback research

Completed-H1 impulse and H4->H1-pullback->M5->M1 structures can produce 45–55% WR on small selective samples, but signal density collapses well below the monthly floor. No configuration had enough raw opportunities to sustain 8 trades in every month while preserving the high-quality filters.

## Causal MTF state-selector stress test

A causal state classifier was trained on 2017 MTF features and thresholded/validated on 2018.

Features used only information available before entry:
- H4/H1 trend/ADX/DI;
- M5 body/range/ATR/RSI/EMA distance/breakout distance/tick-volume;
- direction-relative state;
- causal time-of-day features.

Validation AUC was only about **0.52**.

At thresholds dense enough to guarantee >=8 trades per month, WR stayed around **25–26%** and DD approached 100%.

Machine learning therefore did not reveal a hidden high-frequency 3R edge and was rejected rather than used to overfit 2017–2020.

## Current hard frontier

The research now shows three distinct regions:

| Region | Approx WR | Monthly floor | DD |
|---|---:|---:|---:|
| Elite selective MTF setups | 52–60%+ | 0 | <25% possible |
| New M1 deep-displacement compromise | 45–48% | 1–2 | ~48–70% |
| Genuine >=8/month setups | 27–40% | 8+ | ~100% |

The new M1-native 78.6% displacement family moved the frequency frontier substantially from ~30% WR toward ~40%, but did not bridge the final gap to 50% and did not solve drawdown.

## Structural DD constraint

At 5% risk per trade, six consecutive full SLs create:

`1 - 0.95^6 = 26.49%`

drawdown before considering any prior unrecovered drawdown.

Therefore any strategy with enough trades to generate long loss sequences must have exceptionally strong sequencing/anti-clustering behavior to satisfy DD <25%. The dense 27–40% WR systems all generate loss clusters far beyond this limit.

## Conclusion

This batch found **no honest strict pass**.

The strongest genuinely new direction is M1-native deep-displacement with MTF context. It improves high-frequency WR to ~40% and selective WR to ~47.5%, but the user's complete target remains unmet.

No BE, protected stop, artificial partial-win accounting, outcome look-ahead, or 2021+ tuning was used.

2021–2026 remains sealed.
