# CASIO v3 Research Engine

CASIO v3 now has a Python research engine for the **current product version using the v2 regime-first MTF rule baseline**.

The purpose is not to search for the most beautiful historical equity curve. The purpose is to answer specific strategy questions, reject fragile configurations and surface candidates that remain useful across different samples.

## 1. Files

```text
casio/v3_core.py       causal MTF feature construction
casio/v3_strategy.py   v3 / v2-rule signal logic
casio/v3_backtest.py   M5 execution simulator + metrics
casio/v3_research.py   ablations, candidate search, OOS + Monte Carlo
casio/research_cli.py  CLI entrypoint
```

## 2. Required data

The research engine requires:

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

GitHub cannot automatically read TradingView's private historical chart feed. Normal live TradingView use needs no CSV, but automated Python research needs an independent historical dataset.

## 3. Causality and lookahead

The engine is designed to avoid intentional future-data access.

Higher-timeframe values are made available only after the corresponding H1/H4 bar has closed. The pivot-zone experiment also uses a confirmed pivot proxy rather than reading a future swing before it would have been known.

This is still not a claim of perfect Pine parity. TradingView feed construction and `request.security()` behavior should be checked against exported TradingView results before calling the two implementations exact.

## 4. Baseline

The baseline is:

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

The live v3 FAST Pine should not be silently changed merely because a research run finds a different historical winner.

## 5. Direct ablation experiments

CASIO tests one strategic idea at a time before looking at combinations.

### H4 veto

```text
ON vs OFF
```

Question: does the higher-timeframe restriction materially improve expectancy, PF and drawdown enough to justify fewer trades?

### H1 value model

```text
EMA/ATR baseline
vs
causal pivot-zone proxy
```

Question: does a swing/pivot-derived value model improve results without introducing lookahead?

### Sweep freshness

```text
1, 2, 3, 4, 5 M15 bars
```

Question: is the baseline value of 3 sitting on a stable parameter plateau or merely a historical spike?

### M5 confirmation

```text
ON vs OFF
```

Question: does the extra confirmation improve Scalping expectancy after the opportunity/entry trade-off is considered?

### Intraday minimum usable R:R

```text
2.00
2.25
2.50
2.75
3.00
```

### Session profiles

Current bounded profiles include:

```text
baseline  London 07:00-11:00 | NY 12:30-16:30 UTC
early     London 06:00-10:00 | NY 12:00-16:00 UTC
late      London 08:00-12:00 | NY 13:00-17:00 UTC
wide      London 06:00-12:00 | NY 12:00-17:00 UTC
```

These are research candidates, not a claim that one is universally optimal.

## 6. Candidate search

After the direct ablations, the engine builds combinations across:

```text
H4 veto
H1 value model
sweep freshness
M5 confirmation
minimum Intraday R:R
session profile
```

The full Cartesian space can grow quickly, so the workflow evaluates a deterministic bounded sample. Default:

```text
64 candidates
```

This can be changed through CLI or GitHub Actions manual dispatch.

## 7. Development, sequential validation and final OOS

After a 30-day feature warmup, available history is split conceptually into:

```text
first 80% -> development / candidate research
last 20%  -> final untouched OOS
```

Within development data, the engine evaluates several later sequential validation slices to penalize candidates that work only in one portion of history.

The important guardrail is:

```text
candidate ranking happens BEFORE final OOS is opened
```

The final 20% is therefore not used to choose which candidate looks best.

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

This means a total round-trip research friction assumption of 1 basis point of entry price, converted into R based on that trade's risk distance.

This is **not** claimed to match a live broker exactly. Replace it with a measured assumption appropriate to the actual XAUUSD feed/broker.

For Scalping, the engine automatically writes a cost-sensitivity report using multiples of the baseline friction assumption.

## 10. Metrics

Candidate evaluation considers:

```text
trade count
win rate
expectancy in R
profit factor
maximum drawdown in R
yearly stability
Intraday/Scalping mode stability
sequential validation stability
final OOS result
```

Raw win rate is not the optimization objective.

## 11. Robustness score

The current ranking combines several dimensions rather than maximizing one statistic. The score includes weights for:

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

The exact formula is implementation logic, not a statistically calibrated probability.

A robustness score of 80/100 does **not** mean an 80% probability of future success.

## 12. Final OOS verdict

After ranking on development data, the best candidate is tested on the untouched final OOS segment.

Possible verdicts:

```text
CANDIDATE_FOR_REVIEW
ROBUST_BUT_NOT_MATERIALLY_BETTER
REJECT_OR_INSUFFICIENT
```

A candidate needs meaningful OOS evidence before it can reach review status.

## 13. Monte Carlo stress diagnostic

After a candidate has been selected, CASIO performs 1,000 bootstrap simulations from its historical **net-R** trade distribution.

Each simulation records:

```text
total R
maximum drawdown in R
minimum equity in R
```

The summary includes statistics such as:

```text
probability of positive simulated total R
5th / 50th / 95th percentile total R
50th / 90th / 95th percentile max drawdown
```

This helps answer a different question from the normal backtest:

> What could drawdown look like if the historical trade outcomes arrive in less favorable combinations?

It is still only a bootstrap diagnostic from historical trades. It is **not** a calibrated forecast of future performance and it does not rescue a weak OOS candidate.

## 14. No automatic live mutation

This is a hard guardrail:

```text
research -> report -> human review -> possible future Pine change
```

Not:

```text
research -> silently rewrite live settings -> auto-deploy
```

`auto_deploy` is explicitly false in the generated research summary.

This prevents the latest few trades from turning CASIO into a constantly self-overfitting system.

## 15. Outputs

A successful run writes:

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

`priority_questions.json` is intended to directly answer the eight current strategy questions using measured data rather than intuition.

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

Workflow:

```text
.github/workflows/v3-research.yml
```

It runs:

- when relevant v3 research code or `data/xauusd_m5.csv` changes,
- manually,
- daily at 21:43 UTC.

If the M5 dataset is missing, the workflow reports that research was skipped. It does not fabricate results.

## 18. What remains before real conclusions

The engine is implemented, but actual claims about which rules are better require real, sufficiently long XAUUSD M5 history.

Until that file is present, CASIO can say what it **will test**, not what the data has proven.

After real data is added, the next quality check should be Pine/Python parity validation over the same period before promoting any research conclusion into the live strategy.
