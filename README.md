# CASIO

CASIO is an experimental **XAUUSD strategy research and live-signal system** built around TradingView, a Python robustness engine, a Vercel webhook backend, Google Apps Script email alerts, and an automatic TradingView-to-CSV market-data pipeline.

> Current product version: **CASIO v3**. The live v3 strategy still uses the **v2 regime-first MTF rule set** as its baseline trading logic. Research software only; historical or simulated performance does not guarantee future results.

## What to use

### Live TradingView dashboard — CASIO v3 FAST

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Recommended setup:

```text
Symbol: XAUUSD
Chart: M15
Mode: AUTO
```

v3 FAST is the primary day-to-day `indicator()`. It keeps the same H4/H1/M15/M5 regime-first rules while reducing TradingView load by bundling MTF requests and limiting requested history.

### Automatic M5 collector

```text
pine/CASIO_XAUUSD_M5_FEED.pine
```

Run this once on the **same XAUUSD feed, 5-minute chart**, create an alert using **Any alert() function call**, and point it to the existing CASIO Vercel webhook. TradingView then sends every newly closed M5 bar automatically.

```text
TradingView M5 alert
    -> Vercel
    -> Google Apps Script
    -> CASIO XAUUSD M5 Google Sheet
    -> Vercel CSV export
    -> GitHub scheduled sync
    -> data/xauusd_m5.csv
    -> CASIO v3 research
```

The browser does not need to stay open after the TradingView alert is created.

**Historical caveat:** TradingView script alerts fire on realtime bars only. This collector automatically maintains data from activation forward; it cannot backfill years of past bars. A one-time historical M5 export can still be merged later, and the automatic sync will preserve/deduplicate it.

### Automated research — CASIO v3 Python engine

```text
casio/v3_core.py
casio/v3_strategy.py
casio/v3_backtest.py
casio/v3_research.py
casio/research_cli.py
```

This engine rebuilds M15/H1/H4 causally from **M5 OHLC**, reproduces the current v2-rule baseline in Python, runs ablations, evaluates bounded candidate combinations, performs walk-forward checks, keeps the final 20% as an untouched OOS segment, applies configurable trading friction, stress-tests the selected trade distribution with Monte Carlo bootstrap simulations, and ranks candidates by robustness rather than raw win rate.

Run it with:

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

`1.0` bps is only a research assumption. Replace it with friction measured from the broker/feed you actually use.

### Historical Pine reference — v2 MTF

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

This heavier `strategy()` is retained as the TradingView historical reference for the rule set that v3 currently uses. It provides Strategy Tester and the on-chart rolling audit, but it is slower than v3 FAST.

### Legacy baseline — v1

```text
pine/CASIO_XAUUSD_v1.pine
```

v1 is kept only for comparison.

## Strategy hierarchy

CASIO is **regime-first**, not an equal-vote MTF system:

```text
XAUUSD M15
   |
   +-- H1 + M15 qualify as range? -- YES --> SCALPING
   |                                  |
   |                                  +-- M15 edge sweep
   |                                  +-- M5 confirmation
   |                                  +-- target range mean
   |
   +-- otherwise --------------------> INTRADAY
                                      |
                                      +-- H4 directional context
                                      +-- H1 veto/value/liquidity
                                      +-- M15 sweep + BOS
                                      +-- London / New York
                                      +-- usable R:R veto
```

A score never overrides a mandatory veto.

## Current baseline rules

### Intraday

A long currently requires:

```text
H4 bullish
H1 not bearish
H1 value/pullback condition
recent M15 sell-side sweep
bullish M15 BOS/confirmation
London or New York primary window
>= 1:2.5 room before opposing H1 liquidity
score >= 80
```

Short is the inverse. Preferred target is approximately 1:3, capped by nearer H1 opposing liquidity.

### Scalping

```text
H1 compressed/ranging
M15 low-ADX compressed range
M15 sweep/reclaim of a range edge
M5 direction confirmation
>= 1:1.3 to range mean
score >= 85
```

Scalping is a separate mean-reversion engine, not simply Intraday with a smaller R:R.

## What the v3 research engine tests automatically

The research engine directly targets the current priority questions:

1. H4 veto ON vs OFF.
2. H1 EMA/ATR value proxy vs a causal pivot-zone proxy.
3. Several London/New York UTC session profiles.
4. `sweepFreshBars` = 1, 2, 3, 4, 5.
5. M5 confirmation ON vs OFF.
6. Intraday minimum usable R:R from 2.0 to 3.0.
7. Scalping expectancy under multiple trading-cost assumptions.
8. Stability across years, strategy modes, walk-forward folds and Monte Carlo trade-sequence stress tests.

It also samples bounded combinations of those dimensions and ranks them using a robustness score based on expectancy, profit factor, drawdown, walk-forward results, sample size, yearly stability and mode stability.

## Anti-overfitting guardrail

CASIO research **does not automatically deploy the historically best-looking settings**.

```text
Development data
    -> ablations + candidate search
    -> walk-forward validation
    -> robustness ranking
    -> choose candidate
    -> open untouched final OOS 20%
    -> Monte Carlo stress diagnostic
    -> CANDIDATE_FOR_REVIEW / REJECT
```

The selected candidate is written to reports, but `auto_deploy` is always false. Live Pine is never silently rewritten by the optimizer.

Generated reports include:

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

Monte Carlo is a bootstrap diagnostic based on historical net-R trades. It is not a calibrated forecast of future returns.

## Automatic GitHub data + research

`.github/workflows/market-data-sync.yml` runs daily at **21:20 UTC** and merges the realtime TradingView M5 store into:

```text
data/xauusd_m5.csv
```

If new bars are committed, the push automatically triggers `.github/workflows/v3-research.yml`. The research workflow also has a weekly scheduled safety run and can be launched manually.

The market sync client is:

```text
casio/sync_market_data.py
```

The public market-only CSV proxy is:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?export=m5
```

The private Apps Script token stays inside Vercel environment variables and is not exposed through this CSV endpoint.

## Data contract for v3 research

```csv
timestamp,open,high,low,close,volume
2026-01-02T00:00:00Z,2624.10,2625.00,2623.80,2624.70,0
```

Requirements:

```text
M5 bars
timestamp = UTC bar-open time
OHLC required
volume optional
chronological multi-year history strongly preferred
```

The engine resamples M5 into M15, H1 and H4 with no intentional future-data access. M5 is also used to resolve stop/target execution at finer resolution than M15.

## Important parity limitation

The Python v3 engine is designed to mirror the live v3/v2-rule logic, but exact tick-for-tick parity with TradingView is **not yet claimed** until it is validated against exported TradingView signals/trades. Feed differences, Pine `request.security()` mapping details and broker execution can still create differences.

## Live alerts

```text
TradingView v3 FAST
      |
      v
Vercel /api/tradingview
      |
      +-- token/schema validation
      +-- runtime logging
      +-- Google Apps Script relay
                 |
                 v
       farhanshoffi@moe.gov.my
```

v3 emits `casio.tv.v3`; the M5 collector emits `casio.market.v1`.

Whenever Pine alert logic changes, recreate the TradingView alert because TradingView stores a snapshot of the script when the alert is created.

## Project structure

```text
pine/
  CASIO_XAUUSD_v3_FAST.pine     primary live dashboard
  CASIO_XAUUSD_M5_FEED.pine     automatic realtime M5 collector
  CASIO_XAUUSD_v2_MTF.pine      v2-rule TradingView research reference
  CASIO_XAUUSD_v1.pine          legacy baseline

casio/
  v3_core.py                     causal MTF feature preparation
  v3_strategy.py                 v3 / v2-rule signal logic
  v3_backtest.py                 M5 execution + R metrics
  v3_research.py                 ablations, candidate search, OOS + Monte Carlo
  research_cli.py                v3 research command line
  sync_market_data.py            Vercel CSV -> GitHub dataset merger
  strategy.py/backtest.py/...    legacy Python v1 research engine

api/tradingview.py               Vercel signals + M5 bar receiver + CSV proxy
apps-script/Code.gs              email delivery + M5 Google Sheet store
.github/workflows/market-data-sync.yml
.github/workflows/v3-research.yml
```

## Documentation

- [`docs/STRATEGY_V3.md`](docs/STRATEGY_V3.md) — understand the current v3 strategy and v2-rule baseline.
- [`docs/RESEARCH_V3.md`](docs/RESEARCH_V3.md) — research methodology, outputs and guardrails.
- [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md) — live TradingView operation.
- [`docs/CASIO_V3_EMAIL.md`](docs/CASIO_V3_EMAIL.md) — Vercel + Apps Script email setup.
- [`data/README.md`](data/README.md) — automatic M5 collection and historical data format.
