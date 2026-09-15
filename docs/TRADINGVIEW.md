# CASIO + TradingView

TradingView is the **primary CASIO interface**. CASIO v2 is designed to stay on an XAUUSD **M15 chart** while pulling H4, H1 and M5 context internally.

Primary script:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Legacy comparison script:

```text
pine/CASIO_XAUUSD_v1.pine
```

## Quick start

1. Open **XAUUSD** in TradingView.
2. Set chart timeframe to **15 minutes**.
3. Open **Pine Editor**.
4. Paste `pine/CASIO_XAUUSD_v2_MTF.pine`.
5. Save and choose **Add to chart**.
6. Set `Strategy mode = AUTO`.
7. Leave the chart on M15 for normal use.

You do not need separate H4/H1/M5 charts for CASIO. The script reads them with internal multi-timeframe requests.

## What AUTO means in v2

AUTO is regime-first:

```text
H1 range regime
+ M15 range regime
        |
        +--> true  -> SCALPING
        +--> false -> INTRADAY
```

This is intentionally different from v1, which used a simpler single-timeframe regime classifier.

## Timeframe roles

```text
H4  directional context only
H1  structure, value, liquidity and range context
M15 primary execution timeframe
M5  confirmation for range/scalping entries
```

### H4

H4 establishes the major directional bias using trend alignment. It is context, not an entry trigger.

### H1

H1 decides whether the higher-timeframe structure supports or vetoes the H4 direction. It also provides value/pullback location, opposing liquidity targets and the higher-timeframe range classification.

### M15

M15 is where CASIO actually looks for liquidity sweeps, BOS/confirmation, session eligibility and trade execution.

### M5

M5 is used as an execution confirmation for the Scalping engine. It is not a mandatory extra confirmation for normal Intraday entries because excessive confirmation can make entries late and damage R:R.

## Intraday strategy

A valid long requires all mandatory logic to pass before score matters:

```text
H4 bullish
+ H1 not bearish
+ H1 value/pullback condition
+ recent M15 sell-side liquidity sweep
+ bullish M15 BOS/confirmation
+ London or New York session
+ >= 1:2.5 usable R:R to opposing H1 liquidity
+ score >= configured minimum
= LONG
```

Short is the inverse.

Preferred target is approximately 1:3 R:R, but CASIO caps the target at nearer opposing H1 liquidity. If the available room is less than the configured minimum, the trade is rejected.

## Scalping strategy

Scalping is mean reversion and only activates in a proper range:

```text
H1 compression/range
+ M15 low-ADX compressed range
+ sweep beyond M15 range edge and reclaim
+ M5 reversal confirmation
+ >= 1:1.3 to M15 range mean
+ score >= configured minimum
= SCALP
```

The target is the range mean rather than a trend-continuation target.

## Vetoes and score

Do not interpret the score as "probability of winning".

The sequence is:

```text
1. regime selection
2. mandatory structural checks / vetoes
3. setup score
4. signal
```

Example:

```text
H4 bullish
H1 bearish
M15 bullish trigger
```

CASIO returns `WAIT` because H1 vetoes the long. A high M15 score cannot override that contradiction.

## TradingView dashboard

The v2 dashboard is rendered directly on the chart. Depending on current state it reports items such as:

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
LAST 100
WIN RATE
EXPECTANCY
PROFIT FACTOR
MAX DD
INTRADAY WR
SCALPING WR
AUDIT
```

`WAIT` is an intended output. CASIO is not designed to always find a trade.

## Rolling audit

CASIO stores up to 200 closed-trade R results inside Pine. The newest rolling window, normally 100 trades, is compared with the previous window.

Audit states:

```text
INSUFFICIENT  fewer than the configured minimum trades
HEALTHY       current expectancy/PF acceptable, no material degradation
WARNING       win rate or expectancy deteriorated materially
CRITICAL      PF below threshold or expectancy <= 0
```

The audit is diagnostic. It does not rewrite the strategy automatically.

## Strategy Tester

Because the Pine script uses `strategy()`, TradingView Strategy Tester is the primary full-history performance view for v2.

Evaluate more than win rate:

```text
net profit / return
profit factor
maximum drawdown
number of trades
average trade / expectancy
Intraday contribution
Scalping contribution
behavior across different periods
```

Keep v1 temporarily on a separate chart/layout if you want an A/B baseline.

## Why the dashboard may take time to load

CASIO v2 performs significantly more work than a normal indicator. On load or timeframe change, TradingView must replay the strategy over chart history and resolve multiple timeframe requests.

Conceptually:

```text
M15 historical bars
-> H4 requests
-> H1 requests
-> M5 requests
-> regime classification
-> historical entries/exits
-> rolling 200-trade history
-> current/previous audit windows
-> dashboard render
```

This is why the dashboard can appear a few seconds after the chart itself.

### When you change timeframe

Changing timeframe forces recalculation. More importantly, CASIO v2 has an M15 chart guard: the actual trading conditions are intended to execute from M15.

Normal workflow:

```text
stay on XAUUSD M15
let CASIO read H4/H1/M5 internally
```

If you manually switch to H1/H4/M5, treat it as visual inspection only, not the intended CASIO execution chart.

## Create the TradingView alert

After adding the latest v2 script:

```text
Create Alert
Condition: CASIO XAUUSD v2 — Regime-First MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the CASIO Vercel endpoint configured for this project.

Important: TradingView alerts use a snapshot of the Pine script. **Whenever the Pine alert logic changes, delete/recreate the alert.** Updating the source code alone does not update an already-created TradingView alert.

## v2 alert payload

Confirmed setups send `casio.tv.v2` JSON with fields including:

```text
symbol / ticker / timeframe / bar_time
mode
direction
regime
session
score
entry
stop
target
rr
h4_bias
h1_bias
m15_adx
rolling win_rate
expectancy_r
profit_factor
audit_status
```

Only confirmed setups are emitted; `WAIT` states do not generate trade emails.

## Live architecture

```text
TradingView XAUUSD M15
      |
      |-- CASIO v2 Pine
      |     |-- H4/H1/M15/M5 analysis
      |     |-- Intraday / Scalping routing
      |     |-- BUY / SELL / WAIT
      |     |-- rolling audit
      |     +-- Strategy Tester
      |
      +-- alert() JSON
              |
              v
        Vercel /api/tradingview
              |
              +-- validate + log
              |
              +-- Apps Script relay
                        |
                        v
              farhanshoffi@moe.gov.my
```

See `docs/CASIO_V2_MTF_EMAIL.md` for email setup and `docs/STRATEGY.md` for the complete strategy rationale.

## TradingView vs Python backtest

The current Python engine in `casio/` represents the earlier deterministic research model. It is not yet a 1:1 port of the v2 MTF Pine strategy.

Therefore the following can differ:

```text
trade count
entry timing
win rate
profit factor
drawdown
```

For the current v2 strategy, use TradingView Strategy Tester plus the on-chart rolling audit as the primary measurements.

> Research software only. Historical performance does not guarantee future results.
