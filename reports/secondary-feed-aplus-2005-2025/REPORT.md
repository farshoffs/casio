# CASIO A+ Scale-Out — Secondary-Feed Stress Test

Status: **research only — do not deploy from this report**.

This report continues the `APLUS_CORE + SCALE_2R_RUN4R` experiment:

- London A+ candidate profile.
- 20% realized at +2R.
- Remaining 80% moves to breakeven and targets +4R.
- Conservative stop-first ordering when stop and target are both touched inside the same M5 bar.
- 1 bp round-trip cost assumption.
- Secondary MT4/Octa-style XAUUSD M5 archive normalized from EET/EEST server time to UTC.
- Canonical Dukascopy CSV remains unchanged and remains the feed for live/final validation.

## Why this test matters

The original 2020 Dukascopy research was promising:

- Development: 72 trades, 45.83% WR, +2.03R average winner, +0.366R expectancy, PF 1.65, DD 10.54R.
- Later 2020 validation: 24 trades, 50.0% WR, +2.47R average winner, +0.696R expectancy, PF 2.30, DD 3.24R.

The secondary-feed archive lets us ask whether that behavior survives different market eras and a different broker feed.

## Annual stress-test results

| Year | Trades | WR % | Expectancy R | PF | Max DD R |
|---:|---:|---:|---:|---:|---:|
| 2005 | 19 | 36.84 | -0.243 | 0.646 | 8.14 |
| 2006 | 25 | 48.00 | +0.379 | 1.690 | 6.29 |
| 2007 | 58 | 41.38 | +0.486 | 1.767 | 10.11 |
| 2008 | 74 | 35.14 | -0.127 | 0.811 | 17.18 |
| 2009 | 93 | 26.88 | -0.315 | 0.595 | 28.26 |
| 2010 | 95 | 37.89 | +0.008 | 1.011 | 23.52 |
| 2011 | 89 | 40.45 | +0.258 | 1.404 | 10.16 |
| 2012 | 109 | 30.28 | -0.064 | 0.916 | 20.68 |
| 2013 | 90 | 32.22 | -0.053 | 0.928 | 15.80 |
| 2014 | 93 | 32.26 | +0.023 | 1.032 | 25.61 |
| 2015 | 93 | 39.78 | +0.189 | 1.287 | 10.03 |
| 2016 | 83 | 39.76 | -0.094 | 0.854 | 15.26 |
| 2017 | 120 | 34.17 | +0.006 | 1.008 | 21.55 |
| 2018 | 89 | 32.58 | +0.043 | 1.059 | 12.98 |
| 2019 | 97 | 34.02 | +0.001 | 1.002 | 11.78 |
| 2020 | 106 | 38.68 | +0.229 | 1.352 | 13.37 |
| 2021 | 100 | 35.00 | +0.082 | 1.116 | 17.63 |
| 2022 | 111 | 37.84 | +0.059 | 1.091 | 18.25 |
| 2023 | 116 | 31.90 | -0.177 | 0.766 | 29.54 |
| 2024 | 120 | 29.17 | -0.195 | 0.743 | 30.45 |
| 2025 | 99 | 32.32 | -0.223 | 0.692 | 31.56 |

Across 2005–2025 the model was positive in 12 of 21 calendar years. The weighted net expectancy is approximately flat overall because the 2023–2025 deterioration erased much of the earlier edge. This is a useful failure: the A+ setup is not a universal regime-independent strategy.

## Key diagnosis

Management changes alone do not solve the deterioration. A tuning sweep around partial size, first target, runner target and post-partial stop improved some development statistics but remained negative in the 2023–2025 secondary-feed periods.

The problem is therefore primarily **setup selection / market regime**, not simply the 20%@2R + 80%@4R exit structure.

### Daily regime clue

A promising regime feature emerged from the secondary data: prior-day EMA20/EMA50 separation normalized by daily ATR. The A+ model behaved much better when this value was in a moderate trend zone around roughly `0.6–0.9 ATR`; extremely weak or excessively stretched daily regimes were materially less stable. This is a research hypothesis, not a production rule yet.

A second observation is that the short side degraded badly during 2023–2025. This must not be solved by hard-coding `long only`; instead the next research phase should determine which higher-timeframe regime or liquidity condition reliably identifies when shorts are structurally poor.

### Strong-trend continuation follow-up

A focused 2023–2025 study widened the pullback continuation entry from the original `extension <= 1.1 ATR` to an extended continuation band of `1.1–1.8 ATR`.

Results for extended pullbacks:

- 2023: 66 candidates, 34.85% WR, +0.067R expectancy, PF 1.10.
- 2024: 55 candidates, 32.73% WR, -0.063R expectancy, PF 0.91.
- 2025: 56 candidates, 44.64% WR, -0.007R expectancy, PF 0.99.

Adding a very-strong weekly-trend gate improved 2024/2025 somewhat but still did not create a robust standalone edge:

- 2024 strong-trend extended pullback: 45 candidates, 35.56% WR, +0.030R expectancy, PF 1.04.
- 2025 strong-trend extended pullback: 47 candidates, 46.81% WR, +0.096R expectancy, PF 1.17.

Conclusion: there is evidence that strong-trend continuation deserves its own playbook, but simply loosening the extension cap is not enough.

## Next research phase

Keep the current live model frozen. Treat the scale-out A+ model as one playbook inside a future regime router:

1. **Moderate directional regime** → A+ London pullback/sweep scale-out.
2. **Strong directional expansion** → separate momentum-continuation playbook with its own entry geometry and target logic; do not reuse the same sweep/extension rules.
3. **Compression/range** → separate range-liquidity playbook.
4. **No clean regime** → WAIT.

The next strong-trend playbook should test pullback depth, displacement quality, daily/weekly expansion state, and liquidity runway together rather than one threshold at a time.

Future promotion requires the same rule set to survive both the canonical Dukascopy backfill and this secondary broker feed. No secondary-feed parameter should be pushed directly into live/email without that cross-feed confirmation.
