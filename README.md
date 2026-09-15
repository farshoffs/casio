# CASIO

CASIO is an experimental **XAUUSD strategy research and live-signal system** built around TradingView, with regime-first multi-timeframe analysis, a Vercel webhook backend, and Google Apps Script email alerts.

> Research software only. Historical or simulated performance does not guarantee future results.

## Which CASIO script should I use?

### Daily/live use — v3 FAST

Use:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Run it on:

```text
Symbol: XAUUSD
Chart timeframe: 15 minutes
Strategy mode: AUTO
```

v3 FAST is a lightweight `indicator()` intended for the fastest TradingView dashboard experience. It keeps only the **live MTF decision engine** inside Pine, bundles higher/lower-timeframe requests, caps the amount of requested MTF history, and sends confirmed signals to the Vercel backend.

It deliberately does **not** replay strategy trades or rebuild a rolling 200-trade audit on every chart load.

### Research/backtest — v2 MTF

Use:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

v2 is the heavier `strategy()` version. Use it when you want:

```text
TradingView Strategy Tester
rolling last-100 audit
win rate / expectancy / PF / max DD
Intraday vs Scalping performance comparison
```

### Legacy baseline — v1

```text
pine/CASIO_XAUUSD_v1.pine
```

v1 is retained only as a simpler comparison baseline.

## Important TradingView limitation

The actual on-chart Pine indicator cannot be moved completely to Vercel or GitHub and still behave as the same TradingView dashboard. Pine cannot synchronously call an arbitrary Vercel/GitHub API and wait for the result to draw the current panel.

Therefore CASIO uses a **split architecture**:

```text
TradingView M15
   |
   |-- v3 FAST: current H4/H1/M15/M5 analysis + dashboard
   |
   +-- confirmed signal alert
           |
           v
      Vercel backend
           |
           +-- validation/logging
           +-- Google Apps Script email relay
```

The performance gain comes from making the TradingView-side code lighter, not from pretending the chart can outsource its synchronous Pine calculation.

## Strategy philosophy

CASIO is **regime-first**, not "all timeframes vote on every trade".

```text
XAUUSD M15
   |
   +--> Is H1 + M15 a valid range?
   |       |
   |       +--> YES -> SCALPING engine
   |       +--> NO  -> INTRADAY engine
   |
   +--> mandatory vetoes
   +--> setup scoring
   +--> LONG / SHORT / WAIT
```

A high score cannot override a mandatory structural veto.

## Multi-timeframe hierarchy

The current v2/v3 trade logic uses:

```text
H4  -> directional context
H1  -> structure, value location, opposing liquidity and range regime
M15 -> main execution chart: sweep, BOS, session and trade levels
M5  -> execution confirmation for range/scalping setups only
```

### Intraday engine

Simplified long requirements:

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

Preferred target is approximately **1:3 R:R**, but CASIO will not blindly target through nearer opposing H1 liquidity.

### Scalping engine

Scalping is a separate mean-reversion engine:

```text
H1 compressed/ranging
+ M15 low-ADX compressed range
+ M15 sweep/reclaim of a range edge
+ M5 confirmation
+ at least 1:1.3 back toward the range mean
= eligible scalp
```

## v3 FAST performance optimizations

v3 is specifically designed to reduce TradingView load time:

```text
v2: many separate MTF request.security() calls
v3: one bundled H4 request + one bundled H1 request + one bundled M5 request
```

v3 also uses `calc_bars_count` budgets so TradingView does not request unnecessary external-timeframe history for a live dashboard.

Default request budgets:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

These are configurable under **FAST Performance**. Increasing them gives more requested context but may slow recalculation.

## v3 FAST dashboard

The live panel shows:

```text
STATUS
MODE
REGIME
H4 / H1 BIAS
SESSION
ADX / SCORE
SIGNAL
ENTRY
STOP
TARGET
R:R
H1 RANGE
ENGINE
```

Normal day-to-day workflow:

```text
stay on XAUUSD M15
use v3 FAST
let CASIO read H4/H1/M5 internally
```

If you want deep historical statistics, switch to the v2 strategy rather than making the live indicator heavy again.

## TradingView alerts

For v3 FAST create:

```text
Condition: CASIO XAUUSD v3 FAST — Live MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook.

v3 sends schema:

```text
casio.tv.v3
```

The backend currently accepts v1, v2 and v3. v2/v3 signals can be relayed to Google Apps Script when configured.

Whenever Pine alert logic changes, delete/recreate the TradingView alert because TradingView stores a snapshot of the script at alert creation time.

## Vercel backend

`api/tradingview.py` handles the external/background side:

```text
TradingView alert
-> token validation
-> schema validation
-> CASIO runtime log
-> optional Google Apps Script relay
-> email alert
```

The Python entrypoint is declared in `pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

Production email-relay variables:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=<Apps Script token>
```

## Google Apps Script email alerts

`apps-script/Code.gs` accepts current v2/v3 signals and sends confirmed setups to:

```text
farhanshoffi@moe.gov.my
```

The script deduplicates repeated events and queues email delivery.

## v2 research dashboard and audit

v2 stores up to 200 closed-trade R results and compares the newest rolling window against the previous one.

Audit states:

```text
INSUFFICIENT
HEALTHY
WARNING
CRITICAL
```

Use v2 when you want the on-chart rolling audit or Strategy Tester. Do not interpret the setup score as a probability of winning.

## Python research engine

The `casio/` Python package is an earlier deterministic research engine. It is **not yet a 1:1 Python port of the current MTF Pine logic**.

Run it with:

```bash
pip install -r requirements.txt
python -m casio.cli --data data/xauusd.csv --output reports
```

## Project structure

```text
pine/
  CASIO_XAUUSD_v3_FAST.pine  primary fast live indicator
  CASIO_XAUUSD_v2_MTF.pine   full MTF research/backtest strategy
  CASIO_XAUUSD_v1.pine       legacy baseline

api/
  tradingview.py              Vercel webhook + Apps Script relay

apps-script/
  Code.gs                     email webhook + MailApp delivery

casio/
  config.py
  strategy.py
  backtest.py
  audit.py
  cli.py

docs/
  STRATEGY.md
  TRADINGVIEW.md
  CASIO_V2_MTF_EMAIL.md

data/
  README.md

.github/workflows/
  strategy-audit.yml

pyproject.toml                Vercel Python entrypoint
```

## Documentation

- **Understand the strategy:** [`docs/STRATEGY.md`](docs/STRATEGY.md)
- **Use CASIO in TradingView:** [`docs/TRADINGVIEW.md`](docs/TRADINGVIEW.md)
- **Enable email alerts:** [`docs/CASIO_V2_MTF_EMAIL.md`](docs/CASIO_V2_MTF_EMAIL.md)
- **Use the Python research dataset:** [`data/README.md`](data/README.md)

## Current priorities

1. Use v3 FAST for live chart operation and v2 for research/backtesting.
2. Compare v2/v3 signal parity over the same periods.
3. Add realistic spread/slippage assumptions to research tests.
4. Port current MTF rules into Python for independent parity testing.
5. Keep Pine live logic small; move persistence/notifications/background work to Vercel.
