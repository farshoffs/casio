# CASIO v3 Research Engine

CASIO v3 has a Python research engine for the **current product version: v2 regime-first MTF core + v3 adaptive 24h session overlay**.

The goal is not to discover the prettiest historical equity curve. The goal is to answer specific strategy questions, reject fragile configurations and surface candidates that remain useful across different samples, sessions and market regimes.

## 1. Files

```text
casio/v3_core.py            causal MTF feature construction + session config
casio/v3_strategy.py        regime-first + adaptive 24h signal logic
casio/live_signal.py        latest closed-M15 signal evaluator
casio/v3_backtest.py        M5 execution simulator + session/playbook tags
casio/v3_research.py        ablations, candidate search, OOS + Monte Carlo
casio/research_cli.py       research CLI
casio/sync_market_data.py   market-data normalizer/merger
scripts/fetch_dukascopy.mjs automatic XAUUSD M5 downloader
```

## 2. Research data

Primary dataset:

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
- UTC bar-open timestamps,
- OHLC required,
- volume optional,
- chronological multi-year history strongly preferred.

Why M5?

```text
M5 source
  +-- resample -> M15 execution features
  +-- resample -> H1 context
  +-- resample -> H4 context
  +-- resolve stop/target at finer granularity than M15
```

### Automatic source: Dukascopy

The Free-plan architecture does not depend on TradingView alerts or manual CSV export.

```text
Dukascopy XAUUSD bid M5
        -> scripts/fetch_dukascopy.mjs
        -> casio/sync_market_data.py
        -> data/xauusd_m5.csv
        -> CASIO v3 research
```

`.github/workflows/market-data-sync.yml` is configured to maintain the dataset automatically and to backfill from:

```text
2020-01-09 UTC
```

Historical downloads are chunked and paced because public data providers can rate-limit aggressive requests. The workflow should fail rather than silently commit a suspiciously small or malformed dataset.

### Feed caveat

Dukascopy is an independent XAUUSD feed. Its candles can differ from the broker/provider shown in TradingView. Python/Pine results should therefore be compared structurally, not assumed to match tick-for-tick.

## 3. Causality and lookahead

The Python engine is designed to avoid intentional future-data access.

Higher-timeframe values are only made available after their H1/H4 bar has closed. The pivot-zone experiment uses confirmed causal pivots rather than reading an unconfirmed future swing.

This is not a claim of perfect TradingView parity. Feed construction, higher-timeframe mapping and live execution can still differ.

## 4. Current live baseline

```text
Product: CASIO v3
Core: v2 regime-first MTF
Session policy: adaptive_24h
H4 veto: ON
H1 value model: EMA/ATR
sweepFreshBars: 3
M5 Scalping confirmation: ON
Primary Intraday min R:R: 2.5
Primary Intraday min score: 80
Asia: 00:00-06:00 UTC
Asia trend exception: score >= 90, R:R >= 3.0, H1 aligned
London primary: 07:00-11:00 UTC
New York primary: 12:30-16:30 UTC
Transition: all remaining times
Transition trend exception: score >= 90, R:R >= 3.0, H1 aligned, M15 ADX >= 25
```

Scalping remains range-regime driven across sessions.

## 5. Direct ablation experiments

CASIO tests one strategic idea at a time before looking at combinations.

### Session policy

```text
adaptive_24h
vs
primary_only
```

`primary_only` preserves the previous Intraday restriction to London/New York. `adaptive_24h` allows stricter Asia/Transition directional exceptions while leaving Scalping regime-driven 24h.

This directly answers whether more session coverage adds expectancy or merely adds noise.

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

### Sweep freshness

```text
1, 2, 3, 4, 5 M15 bars
```

### M5 confirmation

```text
ON vs OFF
```

### Primary-session minimum usable R:R

```text
2.00
2.25
2.50
2.75
3.00
```

Asia/Transition exception R:R remains stricter at 3.0 in the current research baseline unless those rules are changed explicitly.

### Primary-session window profiles

```text
baseline  London 07:00-11:00 | NY 12:30-16:30 UTC
early     London 06:00-10:00 | NY 12:00-16:00 UTC
late      London 08:00-12:00 | NY 13:00-17:00 UTC
wide      London 06:00-12:00 | NY 12:00-17:00 UTC
```

These are bounded research candidates, not universal claims about the best gold session times.

## 6. Candidate search

The combination search samples across:

```text
H4 veto
H1 value model
sweep freshness
M5 confirmation
primary Intraday minimum R:R
session policy
London/New York primary-window profile
```

The full Cartesian space grows quickly, so the default workflow evaluates a deterministic bounded sample:

```text
64 candidates
```

The selected live baseline is always included.

## 7. Session-level evaluation

The backtester records:

```text
session
playbook
required_score
required_rr
```

The research engine writes:

```text
reports/v3-research/session_performance.csv
```

for:

```text
baseline development
baseline final OOS
selected-candidate development
selected-candidate final OOS
```

This lets CASIO answer questions such as:

```text
Does Asia add positive expectancy?
Does Transition only add drawdown?
Is London more stable than New York?
Does adaptive_24h outperform primary_only after costs?
```

## 8. Development, sequential validation and final OOS

After a 30-day feature warmup:

```text
first 80% -> development / candidate research
last 20%  -> final untouched OOS
```

Within development, later sequential slices are used as walk-forward-style validation windows.

Guardrail:

```text
candidate ranking happens BEFORE final OOS is opened
```

## 9. Execution model

Signals are generated from M15/H1/H4 context, but trades are resolved using M5 bars.

Rules include:

- one position at a time,
- entry at the M15 decision close,
- subsequent M5 bars checked for stop/target,
- if stop and target are both touched in the same M5 bar, the stop wins,
- results stored in R,
- configurable round-trip trading friction deducted in R.

The same-bar stop-first rule is deliberately conservative.

## 10. Trading costs

CLI option:

```bash
--cost-bps 1.0
```

This is a research assumption, not broker-identical spread/slippage. A bid-only historical feed does not automatically model ask spread, commission or order slippage.

Scalping also receives a cost-sensitivity report across multiples of the baseline friction.

## 11. Metrics

Candidate evaluation considers:

```text
trade count
win rate
expectancy in R
profit factor
maximum drawdown in R
yearly stability
Intraday/Scalping stability
session stability
sequential validation stability
final OOS result
```

Raw win rate is not the optimization objective.

## 12. Robustness score

The current score combines:

```text
development expectancy
profit factor
maximum drawdown
sequential validation expectancy
positive validation ratio
sample size
positive-year ratio
positive-mode ratio
positive-session ratio
```

It is not a calibrated probability. `80/100` does not mean an 80% chance of future profitability.

## 13. Final OOS verdict

Possible verdicts:

```text
CANDIDATE_FOR_REVIEW
ROBUST_BUT_NOT_MATERIALLY_BETTER
REJECT_OR_INSUFFICIENT
```

A candidate needs meaningful OOS evidence before review status.

## 14. Monte Carlo stress diagnostic

The selected candidate is stress-tested with 1,000 bootstrap simulations from historical net-R outcomes.

The diagnostic summarizes total-R and drawdown percentiles. It is not a forecast and cannot rescue a weak OOS result.

## 15. No automatic live mutation

Hard guardrail:

```text
research -> report -> human review -> possible future live-rule change
```

Not:

```text
research -> silently rewrite live settings -> auto-deploy
```

`auto_deploy` remains false.

## 16. Outputs

```text
reports/v3-research/REPORT.md
reports/v3-research/research_summary.json
reports/v3-research/priority_questions.json
reports/v3-research/ablations.csv
reports/v3-research/candidates.csv
reports/v3-research/walk_forward.csv
reports/v3-research/session_performance.csv
reports/v3-research/scalping_cost_sensitivity.csv
reports/v3-research/monte_carlo.csv
reports/v3-research/monte_carlo_summary.json
reports/v3-research/best_candidate.json
reports/v3-research/best_candidate_dev_trades.csv
reports/v3-research/best_candidate_oos_trades.csv
```

`priority_questions.json` now includes adaptive-vs-primary-only session results and selected-candidate per-session metrics.

## 17. Run locally

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

## 18. GitHub Actions automation

```text
.github/workflows/market-data-sync.yml
    -> fetch/backfill Dukascopy XAUUSD M5
    -> validate + merge/deduplicate
    -> commit data/xauusd_m5.csv when changed

.github/workflows/v3-research.yml
    -> triggered by dataset commits
    -> triggered by relevant research-code changes
    -> manual dispatch
    -> weekly scheduled safety run

.github/workflows/live-signal.yml
    -> runs around each M15 close
    -> fetches recent M5 directly
    -> evaluates the current adaptive 24h live rules
    -> emails only fresh valid signals
```

The live signal workflow does not need to wait for the daily persistent-dataset sync.

## 19. What remains before strong conclusions

Strong conclusions require:

```text
clean multi-year data
+ enough trades per session
+ sequential/OOS stability
+ realistic cost assumptions
+ Python/Pine cross-checks
+ awareness of Dukascopy vs TradingView feed differences
```

The new Asia and Transition rules are hypotheses. If multi-year OOS data says those sessions reduce expectancy, the research engine should say so and `primary_only` may remain the better candidate.
