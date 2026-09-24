# CASIO Elite MTF Multi-Session Router Research — 2017–2020

## Hard rules

- Start RM100.
- Risk 5% current equity per entry.
- Fixed RR 1:3.
- Real structural SL only.
- No breakeven / protected SL.
- MTF required for every technique: completed H1/H4 context -> M5 setup -> M1 execution/fill.
- Session unrestricted for this batch. Asia, London, New York, overlap and full-day variants were allowed.
- Target WR floor 50% (target band 50–60%; >60% is reported separately rather than rejected).
- Maximum drawdown <25%.
- Minimum 8 completed trades in every calendar month.
- One position at a time.
- 1 bp round-trip cost.
- M1 same-bar SL/TP ambiguity = SL first.
- Development slice only: 2017-01-01 through 2020-12-31. 2021+ remains sealed.

## Search 1 — elite families across all sessions

1,590 configurations / 640 unique MTF setups were replayed.

Families retained from the prior frontier:
- displacement;
- tick-volume breakout;
- Donchian breakout;
- EMA20 / EMA50 pullback;
- FVG continuation;
- RSI2 snap/reclaim;
- inside-bar breakout;
- rolling liquidity sweep;
- failed breakout.

Session buckets:
- Tokyo/Asia;
- London full;
- New York cash;
- London–New York overlap;
- full day.

Strict passes: **0**.

Best all-session quality candidate remained New York displacement:

`DISPLACEMENT__H4_H1ADX__NY_CASH__r786__adx30__bf0.75__body0.8__cd2__lb16__vol1.15`

- 40 trades.
- WR 50.00%.
- +0.607R/trade.
- PF 1.86.
- DD 20.88%.
- 4/4 positive years.
- Average 0.83 trade/month.
- Minimum month 0.

The looser 70.5% retrace version reached 53 trades and 52.83% WR, but DD rose to 29.79%.

Outside New York, the broad elite families did not produce comparable quality:
- best Asia opening displacement/MSS neighborhood: about 43.75% WR with low trade count;
- best London opening displacement/MSS neighborhood: about 40.63% WR, 32 trades, DD ~33%;
- frequent London EMA pullbacks were ~28–31% WR.

## Search 2 — session subwindows

2,112 additional MTF displacement configurations were tested across:
- Asia open / mid / PM;
- London open / AM / PM;
- New York pre-open / opening hour / mid-morning / lunch / PM.

44 configurations met WR >=50%, DD <25% and 4/4 positive-year quality.

All 44 were concentrated in the **New York opening hour**. No Asia or London subwindow produced a comparable multi-year quality frontier.

Examples:

`MSDISP__H4_H1ADX__NY_OPEN60__r786__A26__B0.5__F0.72__L24`
- 18 trades.
- WR 55.56%.
- +0.953R.
- PF 2.68.
- DD 11.84%.
- 4/4 positive years.

`MSDISP__H4_H1ADX__NY_OPEN60__r886__A30__B0.5__F0.72__L12`
- 11 trades.
- WR 81.82%.
- +1.766R.
- PF 8.28.
- DD 6.73%.
- 4/4 positive years.
- Sample too small to satisfy frequency objective.

## Search 3 — cross-session liquidity

A new causal MTF family was tested:
- London open sweeps latest completed Asia range;
- New York open sweeps completed London-morning range;
- Asia open sweeps latest completed New York cash range;
- H1/H4 trend context;
- M5 sweep/reclaim;
- M1 market/retrace/MSS execution;
- SL outside the real sweep extreme.

104 configurations were tested.

Strict quality passes: 0.

Best London cross-session example:
- 10 trades.
- WR 60.00%.
- +1.126R.
- PF 3.23.
- DD 7.39%.
- Frequency far too low.

## Best-of-the-best router

The router used fixed quality priority and one position at a time.

Elite components included:
- NY cash H4/H1-ADX displacement 78.6% retrace;
- NY opening-hour 78.6% and 88.6% displacement;
- NY mid-morning displacement + M1 MSS;
- NY PM displacement;
- best Asia opening MSS;
- best London opening MSS;
- NY lunch MSS;
- NY cash 70.5% displacement.

### Best router inside the requested WR band

NY opening 88.6% + NY mid MSS + NY PM 70.5% + NY lunch MSS:

- 54 trades.
- WR **57.41%**.
- +1.018R/trade.
- DD **13.93%**.
- Minimum month **0**.
- Months >=8: 0/48.

It passes WR and DD but fails frequency decisively.

### Higher-coverage quality core

NY cash/open/mid/PM plus Asia opening MSS:

- 69 trades.
- WR **52.17%**.
- +0.785R/trade.
- DD **20.15%**.
- Minimum month **0**.
- Months >=8: 0/48.

Adding London opening MSS raised total trades to 101, but:
- WR fell to 48.51%.
- DD rose to 34.88%.
- Minimum month remained 0.

This is the point where increasing independent session coverage begins breaking the quality rules before it solves monthly frequency.

## Causal frequency-floor stress test

To test whether the failure was merely poor router design, a frequency-floor policy was added.

Rules:
- elite signals always have priority;
- frequent fallback signals are accepted only while the current calendar month has fewer than 8 completed trades;
- after 8 trades, fallback signals are ignored;
- real 3R SL/TP mechanics remain unchanged.

This is the minimum-pollution way to force monthly trade coverage.

### Quality core + fallback

Using the 69-trade quality core plus the best available high-frequency London/full-day pullbacks:

- 427 trades.
- Minimum month **8**.
- Months >=8: **48/48**.
- WR **30.21%**.
- +0.037R/trade.
- DD **93.20%**.
- Max loss streak 12.

### Larger quality core + fallback

Using NY quality plus Asia/London/lunch components before fallback:

- 455 trades.
- Minimum month **8**.
- Months >=8: **48/48**.
- WR **30.99%**.
- +0.074R/trade.
- DD **88.32%**.
- Max loss streak 16.

Therefore the minimum-8 rule can be forced, but only by admitting lower-quality opportunities that destroy the WR and DD requirements.

## Current frontier

The hard-rule conflict is now explicit:

| Router / technique | Trades | WR | DD | Min trades/month |
|---|---:|---:|---:|---:|
| Best WR-band elite router | 54 | 57.41% | 13.93% | 0 |
| Higher-coverage quality core | 69 | 52.17% | 20.15% | 0 |
| + London opening MSS | 101 | 48.51% | 34.88% | 0 |
| Frequency-floor quality core | 427 | 30.21% | 93.20% | 8 |
| Frequency-floor larger core | 455 | 30.99% | 88.32% | 8 |

Strict pass count: **0**.

## Conclusion

Allowing any session did not solve the target.

The best high-quality MTF signals remain concentrated around the New York opening/cash period. Asia and London provide some positive-expectancy setups, but their quality is not high enough or their frequency is still too low.

The current data does not support a portfolio that simultaneously delivers:
- WR >=50%;
- DD <25%;
- fixed 3R;
- real SL;
- 5% risk;
- and >=8 trades in every month.

The next legitimate research direction should not add weaker setups merely to manufacture frequency. It should search for a genuinely new high-frequency edge or change one of the hard constraints. Until then, the 52–57% WR / 14–20% DD quality frontier is real, but its frequency is far below the requested monthly floor.

2021+ remains sealed.
