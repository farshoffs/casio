# CASIO

CASIO is an experimental **XAUUSD strategy research and live-signal system** built around TradingView, with a regime-first multi-timeframe strategy, rolling performance audit, webhook delivery through Vercel, and Google Apps Script email alerts.

> Research software only. Historical or simulated performance does not guarantee future results.

## Current primary version

Use:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Run it on:

```text
Symbol: XAUUSD
Chart timeframe: 15 minutes
Strategy mode: AUTO
```

CASIO v2 reads other timeframes internally. You do **not** need to switch the chart to H4, H1 or M5 for the strategy to analyse them.

`pine/CASIO_XAUUSD_v1.pine` is retained as a legacy baseline for A/B comparison in TradingView Strategy Tester.

## Strategy philosophy

CASIO is **regime-first**, not "all timeframes vote on every trade".

```text
XAUUSD M15
   |
   +--> Is the market ranging?
   |       |
   |       +--> YES -> SCALPING engine
   |       |
   |       +--> NO  -> INTRADAY engine
   |
   +--> mandatory vetoes
   +--> setup scoring
   +--> BUY / SELL / WAIT
```

The system is intentionally designed to produce many `WAIT` states. A high score cannot override a mandatory veto.

## Multi-timeframe hierarchy

CASIO v2 uses:

```text
H4  -> directional context
H1  -> structure, value location, opposing liquidity and range regime
M15 -> main execution chart: sweep, BOS, session and trade management
M5  -> execution confirmation for range/scalping setups only
```

### Intraday engine

The intraday engine is used when the market is not classified as a valid range.

A long setup requires, in simplified form:

```text
H4 bullish bias
+ H1 not bearish
+ price in acceptable H1 value/pullback area
+ recent M15 sell-side liquidity sweep
+ M15 bullish BOS/confirmation
+ London or New York session
+ at least 1:2.5 usable R:R before opposing H1 liquidity
= eligible LONG
```

Shorts are the inverse.

Preferred intraday target is approximately **1:3 R:R**, but CASIO will not blindly target through closer opposing H1 liquidity. If there is not at least the configured minimum usable room, the trade is vetoed.

### Scalping engine

Scalping is a separate mean-reversion engine, not simply the intraday strategy with a smaller target.

A valid range setup requires:

```text
H1 compressed/ranging
+ M15 low-ADX compressed range
+ M15 sweep of a range edge
+ M5 rejection/confirmation
+ at least 1:1.3 R:R back toward the range mean
= eligible scalp
```

Scalping therefore activates only when both the higher-timeframe and execution-timeframe range conditions agree.

## Mandatory conditions vs score

CASIO uses two layers:

1. **Mandatory conditions / vetoes** decide whether a trade is allowed at all.
2. **Score** ranks the quality of a setup that has already passed the mandatory logic.

This prevents a mathematically high score from approving a structurally contradictory trade.

Example:

```text
H4 bullish
H1 strongly bearish
M15 bullish trigger

Result: WAIT
```

The H1 contradiction is a veto; it is not just a small score penalty.

## Sessions

Intraday entries are restricted to the configured UTC windows:

```text
London:   07:00-11:00 UTC
New York: 12:30-16:30 UTC
```

These can be adjusted in TradingView inputs if needed. Scalping uses its own range conditions rather than requiring the intraday session filter.

## TradingView dashboard

TradingView is the primary day-to-day CASIO interface.

The v2 panel shows the strategy state directly on the chart, including items such as:

```text
MODE
REGIME
H4 BIAS
H1 BIAS
SESSION
M15 ADX / SCORE
SIGNAL
ENTRY
STOP
TARGET
R:R
LAST 100 CLOSED TRADES
WIN RATE
EXPECTANCY (R)
PROFIT FACTOR
MAX DRAWDOWN (R)
INTRADAY WIN RATE
SCALPING WIN RATE
AUDIT STATUS
```

The Pine strategy stores up to 200 closed-trade R results so it can compare the latest rolling window with the preceding window.

Audit states:

```text
INSUFFICIENT  not enough closed trades yet
HEALTHY       positive current performance without material degradation
WARNING       rolling win rate or expectancy deteriorated materially
CRITICAL      profit factor below threshold or non-positive expectancy
```

CASIO does **not** automatically rewrite strategy parameters when the audit deteriorates. Changes should be researched and versioned instead of optimized against only the latest sample.

## Why the dashboard can take time to load

CASIO v2 is heavier than a normal single-timeframe indicator. When TradingView loads or recalculates the strategy, it must:

```text
load chart history
-> calculate M15 features
-> request H4 context
-> request H1 structure/range data
-> request M5 confirmation data
-> replay historical strategy trades
-> rebuild the rolling audit history
-> render the dashboard
```

Changing chart timeframe causes TradingView to recalculate the strategy again. CASIO v2 is designed to operate on **M15**, so leave the chart on M15 during normal use. H4/H1/M5 are already requested internally.

## TradingView alerts

Create the alert from the compiled v2 strategy:

```text
Condition: CASIO XAUUSD v2 — Regime-First MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Whenever Pine alert logic changes, delete/recreate the TradingView alert because TradingView stores a snapshot of the script at alert creation time.

The live path is:

```text
TradingView XAUUSD M15
        |
        | confirmed CASIO v2 signal JSON
        v
Vercel /api/tradingview
        |
        +--> validation + runtime log
        |
        +--> Google Apps Script relay
                    |
                    v
          farhanshoffi@moe.gov.my
```

See [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md) for TradingView setup and [`docs/CASIO_V2_MTF_EMAIL.md`](docs/CASIO_V2_MTF_EMAIL.md) for email/webhook deployment.

## Vercel backend

`api/tradingview.py` accepts `casio.tv.v1` and `casio.tv.v2`, validates XAUUSD signal payloads and relays v2 signals to Google Apps Script when configured.

The Vercel Python entrypoint is declared in `pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

Production environment variables used by the email relay:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=<Apps Script token>
```

The TradingView -> Vercel webhook remains protected separately by the CASIO webhook token.

## Google Apps Script email alerts

`apps-script/Code.gs` sends confirmed v2 signals to:

```text
farhanshoffi@moe.gov.my
```

The script provides:

```text
setupCasio()       initialize recipient + private token
sendTestEmail()    verify MailApp delivery
printWebhookUrl()  print deployed Web App URL + token
```

The webhook deduplicates repeated signals and queues email delivery so the TradingView-facing path remains fast.

## Strategy Tester and performance evaluation

Use TradingView Strategy Tester to evaluate the v2 Pine strategy using TradingView's own historical data.

Do not judge the strategy on win rate alone. Compare at least:

```text
number of trades
net profit / return
profit factor
expectancy / average trade
maximum drawdown
Intraday vs Scalping contribution
stability across periods
```

A lower win rate can still be superior if expectancy and drawdown are better.

## Python research engine

The `casio/` Python package remains a deterministic research/backtest engine and GitHub Action still supports `data/xauusd.csv`.

Important: the current Python engine is based on the earlier single-timeframe research rules. It is **not yet a 1:1 Python port of CASIO v2 MTF**. Therefore do not expect its trades or statistics to exactly match the current TradingView v2 strategy.

For the live v2 strategy, the TradingView Strategy Tester and on-chart rolling audit are currently the primary performance views.

Run the Python research engine with:

```bash
pip install -r requirements.txt
python -m casio.cli --data data/xauusd.csv --output reports
```

## Project structure

```text
pine/
  CASIO_XAUUSD_v2_MTF.pine   primary MTF strategy
  CASIO_XAUUSD_v1.pine       legacy comparison baseline

api/
  tradingview.py              Vercel webhook + Apps Script relay

apps-script/
  Code.gs                     email webhook + MailApp delivery

casio/
  config.py                   legacy Python research thresholds
  strategy.py                 legacy deterministic signal engine
  backtest.py                 backtest simulator + metrics
  audit.py                    rolling audit engine
  cli.py                      local report runner

data/
  README.md                   Python research data contract

docs/
  STRATEGY.md                 detailed strategy explanation
  TRADINGVIEW.md              TradingView operating guide
  CASIO_V2_MTF_EMAIL.md       Vercel + Apps Script email setup

.github/workflows/
  strategy-audit.yml          scheduled Python research audit

pyproject.toml                Vercel Python entrypoint
```

## Documentation

Start here depending on what you want to do:

- **Understand the strategy:** [`docs/STRATEGY.md`](docs/STRATEGY.md)
- **Use CASIO in TradingView:** [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md)
- **Enable email alerts:** [`docs/CASIO_V2_MTF_EMAIL.md`](docs/CASIO_V2_MTF_EMAIL.md)
- **Use the Python research dataset:** [`data/README.md`](data/README.md)

## Current next research priorities

1. Compare v2 against v1 over meaningful historical windows.
2. Measure Intraday and Scalping expectancy separately.
3. Add realistic spread/slippage assumptions where possible.
4. Port v2 MTF rules into the Python backtester for independent parity testing.
5. Optimize Pine MTF requests without changing strategy behavior.
6. Prefer out-of-sample/walk-forward evidence over repeated parameter tuning on the same data.
