# CASIO

CASIO is an experimental **XAUUSD strategy research and live-signal system** built around TradingView for charting, a Python v3 decision/research engine, Dukascopy market data, GitHub Actions automation, and Google Apps Script email delivery.

> Current product version: **CASIO v3**. The live v3 strategy still uses the **v2 regime-first MTF rule set** as its baseline trading logic. Research software only; historical or simulated performance does not guarantee future results.

## Current architecture — TradingView Free friendly

The user does **not** need TradingView alerts or webhooks.

```text
                    CASIO v3
                       |
        +--------------+--------------+
        |                             |
        v                             v
 TradingView Free                Automation
 visual chart only                  |
 XAUUSD M15                          v
 v3 FAST dashboard           Dukascopy XAUUSD M5
                                      |
                         +------------+------------+
                         |                         |
                         v                         v
                  v3 live signal            historical dataset
                  every M15 close           daily sync/backfill
                         |                         |
                         v                         v
                  GitHub Actions          data/xauusd_m5.csv
                         |                         |
                         v                         v
                  Apps Script email       v3 research engine
```

TradingView remains the preferred visual interface, but it is **not** the automation source on the Free plan.

## Live TradingView dashboard

Use:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Recommended:

```text
Symbol: XAUUSD
Chart: M15
Mode: AUTO
```

v3 FAST reads H4/H1/M5 internally and displays the current regime, bias, setup score, signal, entry, stop, target and R:R. No TradingView alert is required for normal chart use.

## Free live signal email engine

Workflow:

```text
.github/workflows/live-signal.yml
```

It runs shortly after each M15 close:

```text
02 / 17 / 32 / 47 minutes past each hour
```

Each run:

```text
fetch latest Dukascopy XAUUSD M5
-> rebuild H4/H1/M15/M5 CASIO context
-> run the same v3/v2-rule baseline
-> reject stale/invalid setups
-> LONG / SHORT / no signal
-> Google Apps Script
-> farhanshoffi@moe.gov.my
```

The signal evaluator is:

```text
casio/live_signal.py
```

Email delivery requires one GitHub Actions secret:

```text
CASIO_GAS_WEBHOOK_URL
```

Set it to the complete Apps Script Web App URL returned by `printWebhookUrl()`, including its private token. Do not commit that URL to source control.

GitHub Actions schedules are suitable for bar-close notification/research automation but are not guaranteed millisecond/second-level execution timing. CASIO rejects signals older than 35 minutes so a badly delayed job cannot send a very stale setup.

## Automatic historical market data

Research data no longer depends on TradingView exporting CSV.

Workflow:

```text
.github/workflows/market-data-sync.yml
```

CASIO automatically downloads **Dukascopy XAUUSD bid M5** data. The first successful run backfills from:

```text
2020-01-09 UTC
```

Later runs overlap the previous few days, merge/deduplicate timestamps and maintain:

```text
data/xauusd_m5.csv
```

The downloader is:

```text
scripts/fetch_dukascopy.mjs
```

and the normalizer/merger is:

```text
casio/sync_market_data.py
```

Dukascopy is an independent feed, so its XAUUSD candles can differ slightly from the broker/feed displayed in TradingView. CASIO therefore does not claim tick-for-tick feed parity.

## Automated research — CASIO v3 Python engine

```text
casio/v3_core.py
casio/v3_strategy.py
casio/v3_backtest.py
casio/v3_research.py
casio/research_cli.py
```

The engine rebuilds M15/H1/H4 causally from M5 data, reproduces the current v2-rule baseline in Python, runs ablations and bounded candidate combinations, uses sequential validation, reserves the final 20% as untouched OOS, applies configurable trading friction, performs Monte Carlo bootstrap stress tests and ranks candidates by robustness rather than raw win rate.

Manual command:

```bash
pip install -r requirements.txt
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research \
  --max-candidates 64 \
  --cost-bps 1.0
```

`1.0` bps is a research assumption, not a claim about a particular broker's real spread/slippage.

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

### Intraday baseline

A long requires:

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

### Scalping baseline

```text
H1 compressed/ranging
M15 low-ADX compressed range
M15 sweep/reclaim of a range edge
M5 direction confirmation
>= 1:1.3 to range mean
score >= 85
```

Scalping is a separate mean-reversion engine.

## Research questions tested automatically

The v3 research engine tests:

1. H4 veto ON vs OFF.
2. H1 EMA/ATR value proxy vs a causal pivot-zone proxy.
3. Alternative London/New York session profiles.
4. `sweepFreshBars` = 1, 2, 3, 4, 5.
5. M5 confirmation ON vs OFF.
6. Intraday minimum usable R:R from 2.0 to 3.0.
7. Scalping expectancy under multiple cost assumptions.
8. Stability across years, modes, sequential validation periods and Monte Carlo trade sequences.

The optimizer never silently changes production settings. `auto_deploy` remains false.

## Historical TradingView reference

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

This heavier `strategy()` remains the TradingView historical reference for the rule family used by v3. It provides Strategy Tester and rolling audit when those TradingView features are available, but it is not the current product version.

`pine/CASIO_XAUUSD_v1.pine` is retained as the legacy baseline.

`pine/CASIO_XAUUSD_M5_FEED.pine` is retained only as an optional collector for accounts that support TradingView alerts; it is **not used by the current Free-plan architecture**.

## Important parity limitation

The Python v3 engine is designed to mirror the current v3/v2-rule logic, but exact tick-for-tick parity with TradingView is not yet claimed. Differences can arise from source-feed candles, higher-timeframe mapping, Pine behavior and execution assumptions.

Before promoting a research candidate, compare both implementations over matching periods and focus on robust conclusions rather than exact trade-for-trade identity.

## Project structure

```text
pine/
  CASIO_XAUUSD_v3_FAST.pine     primary TradingView visual dashboard
  CASIO_XAUUSD_v2_MTF.pine      TradingView historical reference
  CASIO_XAUUSD_M5_FEED.pine     optional paid-alert collector, not required
  CASIO_XAUUSD_v1.pine          legacy baseline

casio/
  v3_core.py                     causal MTF feature preparation
  v3_strategy.py                 v3 / v2-rule signal logic
  live_signal.py                 latest closed-M15 signal evaluator
  v3_backtest.py                 M5 execution + R metrics
  v3_research.py                 ablations, OOS + Monte Carlo
  research_cli.py                research CLI
  sync_market_data.py            market CSV normalizer/merger

scripts/
  fetch_dukascopy.mjs            automatic XAUUSD M5 downloader

apps-script/Code.gs              email delivery

.github/workflows/
  live-signal.yml                free live signal/email scheduler
  market-data-sync.yml           automatic Dukascopy dataset sync
  v3-research.yml                research/robustness automation
```

## Documentation

- [`docs/STRATEGY_V3.md`](docs/STRATEGY_V3.md) — current strategy logic.
- [`docs/RESEARCH_V3.md`](docs/RESEARCH_V3.md) — research methodology and guardrails.
- [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md) — TradingView Free operating instructions.
- [`docs/CASIO_V3_EMAIL.md`](docs/CASIO_V3_EMAIL.md) — Apps Script + GitHub email setup.
- [`data/README.md`](data/README.md) — automatic Dukascopy M5 dataset.
