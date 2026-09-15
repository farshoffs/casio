# CASIO v3 Research Engine

CASIO v3 has a Python research engine for the **current product version using the v2 regime-first MTF rule baseline**.

The purpose is not to search for the prettiest historical equity curve. The purpose is to answer specific strategy questions, reject fragile configurations and surface candidates that remain useful across different samples.

## 1. Files

```text
casio/v3_core.py          causal MTF feature construction
casio/v3_strategy.py      v3 / v2-rule signal logic
casio/v3_backtest.py      M5 execution simulator + metrics
casio/v3_research.py      ablations, candidate search, OOS + Monte Carlo
casio/research_cli.py     research CLI
casio/sync_market_data.py automatic realtime-feed CSV merger
```

## 2. Research data

The engine uses:

```text
data/xauusd_m5.csv
```

Schema:

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2625.00,2623.80,2624.70,0
```

Requirements:

- M5 OHLC bars,
- timestamp is UTC **bar-open** time,
- OHLC required,
- volume optional,
- chronological multi-year history strongly preferred.

Why M5 instead of only M15?

```text
M5 source
  +-- resample -> M15 execution features
  +-- resample -> H1 context
  +-- resample -> H4 context
  +-- resolve stop/target at finer granularity than M15
```

### Automatic collection from TradingView

CASIO now collects **new realtime M5 bars automatically** after one TradingView collector alert is created:

```text
pine/CASIO_XAUUSD_M5_FEED.pine
        -> Vercel
        -> Apps Script Google Sheet
        -> Vercel CSV proxy
        -> .github/workflows/market-data-sync.yml
        -> data/xauusd_m5.csv
```

The market-data sync runs daily at 21:20 UTC and merges/deduplicates the remote bars with any existing local history.

### Historical backfill limitation

TradingView script alerts only trigger on realtime bars. Therefore automatic collection starts from activation forward and cannot reconstruct several years of past history by itself.

A one-time TradingView M5 CSV export can still be added to `data/xauusd_m5.csv`. The automatic sync preserves the old rows and appends future bars. This hybrid approach is the preferred way to get both **historical depth** and **automatic ongoing updates**.

## 3. Causality and lookahead

The engine is designed to avoid intentional future-data access.

Higher-timeframe values are made available only after the corresponding H1/H4 bar has closed. The pivot-zone experiment also uses a confirmed pivot proxy rather than reading a future swing before it would have been known.

This is still not a claim of perfect Pine parity. TradingView feed construction and `request.security()` behavior should be checked against exported TradingView results before calling the two implementations exact.

## 4. Baseline

```text
Product: CASIO v3
Rule family: v2 regime-first MTF
H4 veto: ON
H1 value model: EMA/ATR
sweepFreshBars: 3
M5 Scalping confirmation: ON
Intraday min usable R:R: 2.5
London: 07:00-11:00 UTC
New York: 12:30-16:30 UTC
```

The live v3 FAST Pine is never silently changed merely because a research run finds a different historical winner.

## 5. Direct ablation experiments

CASIO tests one strategic idea at a time before looking at combinations.

### H4 veto

```text
ON vs OFF
```

Does the higher-timeframe restriction improve expectancy, PF and drawdown enough to justify fewer trades?

### H1 value model

```text
EMA/ATR baseline
vs
causal pivot-zone proxy
```

Does a swing/pivot-derived value model improve results without introducing lookahead?

### Sweep freshness

```text
1, 2, 3, 4, 5 M15 bars
```

Is the baseline value of 3 on a stable plateau or merely a historical spike?

### M5 confirmation

```text
ON vs OFF
```

Does the extra confirmation improve Scalping expectancy after the entry/opportunity trade-off?

### Intraday minimum usable R:R

```text
2.00
2.25
2.50
2.75
3.00
```

### Session profiles

```text
baseline  London 07:00-11:00 | NY 12:30-16:30 UTC
early     London 06:00-10:00 | NY 12:00-16:00 UTC
late      London 08:00-12:00 | NY 13:00-17:00 UTC
wide      London 06:00-12:00 | NY 12:00-17:00 UTC
```

These are research candidates, not universal claims.

## 6. Candidate search

After direct ablations, the engine builds combinations across:

```text
H4 veto
H1 value model
sweep freshness
M5 confirmation
minimum Intraday R:R
session profile
```

The full Cartesian space grows quickly, so the workflow evaluates a deterministic bounded sample. Default:

```text
64 candidates
```

This can be changed through CLI or GitHub Actions manual dispatch.

## 7. Development, sequential validation and final OOS

After a 30-day feature warmup:

```text
first 80% -> development / candidate research
last 20%  -> final untouched OOS
```

Within development data, several later sequential validation slices penalize candidates that work only in one portion of history.

The key guardrail is:

```text
candidate ranking happens BEFORE final OOS is opened
```

## 8. Execution model

Signals are generated from M15/H1/H4 context, but trades are resolved using M5 bars.

Rules include:

- one position at a time,
- entry at the M15 decision close,
- subsequent M5 bars checked for stop/target,
- if both stop and target are touched in the same M5 bar, the stop wins,
- results stored in R,
- configurable round-trip trading friction deducted in R.

The same-bar stop-first assumption is deliberately conservative.

## 9. Trading costs

CLI option:

```bash
--cost-bps 1.0
```

This is a research friction assumption, not a claim of live-broker equivalence. Replace it with an estimate measured from the actual XAUUSD broker/feed.

For Scalping, CASIO also writes a cost-sensitivity report across multiples of the baseline friction.

## 10. Metrics

Candidate evaluation considers:

```text
trade count
win rate
expectancy in R
profit factor
maximum drawdown in R
yearly stability
Intraday/Scalping stability
sequential validation stability
final OOS result
```

Raw win rate is not the optimization objective.

## 11. Robustness score

The score combines:

```text
development expectancy
profit factor
maximum drawdown
sequential validation expectancy
positive validation ratio
sample size
positive-year ratio
positive-mode ratio
```

It is not a calibrated probability. A robustness score of 80/100 does **not** mean 80% probability of future success.

## 12. Final OOS verdict

Possible verdicts:

```text
CANDIDATE_FOR_REVIEW
ROBUST_BUT_NOT_MATERIALLY_BETTER
REJECT_OR_INSUFFICIENT
```

A candidate needs meaningful OOS evidence before review status.

## 13. Monte Carlo stress diagnostic

The selected candidate is stress-tested with 1,000 bootstrap simulations from historical **net-R** trade outcomes.

Each simulation records total R, maximum drawdown in R and minimum equity in R. The summary includes percentile outcomes such as median and 95th-percentile maximum drawdown.

This is a robustness diagnostic, not a calibrated forecast, and it does not rescue a weak OOS candidate.

## 14. No automatic live mutation

Hard guardrail:

```text
research -> report -> human review -> possible future Pine change
```

Not:

```text
research -> silently rewrite live settings -> auto-deploy
```

`auto_deploy` is explicitly false.

## 15. Outputs

```text
reports/v3-research/REPORT.md
reports/v3-research/research_summary.json
reports/v3-research/priority_questions.json
reports/v3-research/ablations.csv
reports/v3-research/candidates.csv
reports/v3-research/walk_forward.csv
reports/v3-research/scalping_cost_sensitivity.csv
reports/v3-research/monte_carlo.csv
reports/v3-research/monte_carlo_summary.json
reports/v3-research/best_candidate.json
reports/v3-research/best_candidate_dev_trades.csv
reports/v3-research/best_candidate_oos_trades.csv
```

`priority_questions.json` directly addresses the eight current strategy questions using measured data.

## 16. Run locally

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

## 17. GitHub Actions automation

Two workflows now cooperate:

```text
.github/workflows/market-data-sync.yml
    daily 21:20 UTC
    -> pulls stored TradingView M5 bars
    -> merges/deduplicates data/xauusd_m5.csv
    -> commits only when data changed

.github/workflows/v3-research.yml
    -> triggered by data/xauusd_m5.csv commits
    -> triggered by relevant research-code changes
    -> manual dispatch
    -> weekly scheduled safety run
```

When the dataset is absent or the collector has not been configured yet, the research workflow validates the code but skips performance claims rather than fabricating results.

## 18. What remains before strong conclusions

The automatic feed solves **ongoing collection**, not historical depth. Robust conclusions still need a sufficiently long history covering different XAUUSD regimes.

Best path:

```text
one-time historical M5 backfill
+ automatic realtime M5 collection thereafter
+ Pine/Python parity checks
+ broker-specific cost calibration
```

Only after those steps should a research candidate be considered for promotion into the live v3 rule set.
