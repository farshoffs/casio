# CASIO + TradingView

TradingView remains the primary CASIO interface, but the project now separates **fast live operation** from **heavy research/backtesting**.

## Use v3 FAST for normal charting

Primary live script:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Run it on:

```text
XAUUSD
15 minutes
Strategy mode = AUTO
```

v3 FAST is an `indicator()` rather than a historical strategy simulator. It keeps the current MTF decision engine in TradingView while Vercel handles background webhook/email work.

## Use v2 for Strategy Tester and rolling audit

Research script:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Use v2 when you specifically want:

```text
Strategy Tester
rolling last-100 performance
expectancy / PF / drawdown
Intraday vs Scalping research
```

Because v2 replays historical trades and rebuilds its rolling audit, it is naturally slower to load than v3 FAST.

## Why Vercel cannot render the TradingView dashboard for Pine

Pine cannot synchronously make an arbitrary HTTP request to Vercel/GitHub and wait for the result before drawing the chart panel. Therefore the chart-side decision logic must still execute inside TradingView.

CASIO uses this split instead:

```text
TradingView v3 FAST
    |
    |-- H4/H1/M15/M5 current analysis
    |-- dashboard
    |-- LONG / SHORT / WAIT
    |
    +-- confirmed alert
             |
             v
        Vercel backend
             |
             +-- validation/logging
             +-- Google Apps Script email
```

The speed improvement comes from reducing what Pine has to recalculate.

## v3 FAST optimizations

The fast script makes only three external-timeframe request groups:

```text
H4 -> close + EMA20 + EMA50 in one request
H1 -> close + EMA20 + EMA50 + ATR + range high/low in one request
M5 -> open + close + EMA20 in one request
```

It also uses `calc_bars_count` limits instead of requesting unnecessary external history.

Default FAST budgets:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

These can be changed in the **FAST Performance** settings. Larger values may increase recalculation time.

## Timeframe hierarchy

Both v2 and v3 use the same intended trade hierarchy:

```text
H4  -> directional context
H1  -> structure, value, opposing liquidity, range regime
M15 -> execution chart: sweep, BOS, session and trade levels
M5  -> range/scalping confirmation only
```

You should normally leave the chart on M15. CASIO pulls the other timeframes internally.

## AUTO routing

```text
H1 range regime
+ M15 range regime
        |
        +--> true  -> SCALPING
        +--> false -> INTRADAY
```

## Intraday logic

A long requires:

```text
H4 bullish
+ H1 not bearish
+ H1 value/pullback condition
+ recent M15 sell-side sweep
+ bullish M15 BOS/confirmation
+ London or New York session
+ >= 1:2.5 usable R:R to opposing H1 liquidity
+ score >= configured minimum
= LONG
```

Short is the inverse.

Preferred target is about 1:3, but CASIO caps the target at nearer opposing H1 liquidity.

## Scalping logic

Scalping is a separate mean-reversion engine:

```text
H1 compressed/ranging
+ M15 low-ADX compressed range
+ M15 sweep/reclaim of range edge
+ M5 confirmation
+ >= 1:1.3 to range mean
+ score >= configured minimum
= SCALP
```

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

`WAIT` is an intended output.

## Create the v3 TradingView alert

After adding the latest v3 script:

```text
Create Alert
Condition: CASIO XAUUSD v3 FAST — Live MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook.

v3 emits:

```text
schema = casio.tv.v3
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
```

A configurable M15-bar cooldown prevents repeated alerts from spamming the same setup.

Important: TradingView alerts store a snapshot of the script. Whenever Pine alert logic changes, delete and recreate the alert.

## Vercel background flow

```text
TradingView alert
      |
      v
/api/tradingview
      |
      +-- validate token
      +-- validate v1/v2/v3 schema
      +-- log signal
      +-- relay current v2/v3 signals to Apps Script
                     |
                     v
           farhanshoffi@moe.gov.my
```

Vercel does not make the TradingView panel draw itself. It handles the work that does not need to happen synchronously inside Pine.

## When should I use v2 instead?

Open `pine/CASIO_XAUUSD_v2_MTF.pine` when you want to answer research questions such as:

```text
How many trades?
What is the win rate?
What is the rolling expectancy?
What is the profit factor?
What is the max drawdown?
Which mode contributes more?
```

Then return to v3 FAST for normal live chart usage.

## Why changing timeframe still causes some recalculation

Any Pine script must be recalculated when TradingView changes chart timeframe. v3 should be substantially lighter than v2, but it still needs to rebuild its M15-native series and current MTF context.

The intended workflow remains:

```text
stay on XAUUSD M15
let CASIO read H4/H1/M5 internally
```

See `docs/STRATEGY.md` for the detailed rationale and `docs/CASIO_V2_MTF_EMAIL.md` for the webhook/email setup.

> Research software only. Historical performance does not guarantee future results.
