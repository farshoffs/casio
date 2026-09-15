# CASIO v3 + TradingView

TradingView is the primary **live CASIO v3 interface**. The current v3 live strategy still uses the **v2 regime-first MTF rule baseline**.

CASIO separates fast live charting from deeper automated research:

```text
TradingView v3 FAST -> current signal/dashboard
Python v3 research  -> ablations, candidate search, walk-forward/OOS
v2 Pine strategy    -> TradingView historical reference for baseline rules
```

## 1. Use v3 FAST for normal charting

Primary live script:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

Recommended setup:

```text
Symbol: XAUUSD
Chart: M15
Mode: AUTO
```

v3 FAST is an `indicator()` rather than a historical strategy simulator. It keeps the current MTF decision engine in TradingView while Vercel handles webhook/email work and Python handles deeper independent research.

## 2. Timeframe hierarchy

The current baseline rules use:

```text
H4  -> directional context
H1  -> structure, value proxy, opposing liquidity, range regime
M15 -> primary execution chart: sweep, BOS, session and levels
M5  -> Scalping confirmation only
```

Stay on M15 for normal use. CASIO reads H4/H1/M5 internally.

## 3. AUTO routing

```text
H1 range regime
+ M15 range regime
        |
        +--> true  -> SCALPING
        +--> false -> INTRADAY
```

### Intraday baseline

A long requires:

```text
H4 bullish
H1 not bearish
H1 value/pullback condition
recent M15 sell-side sweep
bullish M15 BOS proxy
London or New York session
>= 1:2.5 usable R:R before H1 opposing liquidity
score >= 80
```

Short is the inverse.

Preferred target is about 1:3, capped by nearer H1 opposing liquidity.

### Scalping baseline

```text
H1 compressed/ranging
M15 low-ADX compressed range
M15 sweep/reclaim of range edge
M5 confirmation
>= 1:1.3 to range mean
score >= 85
```

Scalping is a separate mean-reversion engine.

## 4. v3 FAST performance optimizations

v3 groups external-timeframe calculations:

```text
H4 -> close + EMA20 + EMA50 in one request
H1 -> close + EMA20 + EMA50 + ATR + range high/low in one request
M5 -> open + close + EMA20 in one request
```

It also uses `calc_bars_count` budgets.

Defaults:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

Those settings live under **FAST Performance**. Larger budgets can increase recalculation time.

Changing TradingView chart timeframe still forces Pine recalculation. The intended workflow is simply to remain on M15.

## 5. v3 FAST dashboard

The live panel shows the current decision state, including:

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

`WAIT` is a normal and intentional result.

The score is not a win probability.

## 6. TradingView alert

After adding the latest v3 FAST script:

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

A configurable M15-bar cooldown helps avoid repeated alerts from the same continuing condition.

Important: TradingView stores an alert snapshot. When alert-producing Pine logic changes, delete the old alert and create it again from the latest script.

## 7. Vercel and email path

```text
TradingView v3 FAST
      |
      v
/api/tradingview
      |
      +-- token validation
      +-- v3 schema validation
      +-- runtime logging
      +-- Apps Script relay
                 |
                 v
       farhanshoffi@moe.gov.my
```

See `docs/CASIO_V3_EMAIL.md` for full setup.

## 8. Where historical research now lives

### Python v3 research engine — primary automated research

Use:

```bash
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research
```

It tests the current strategy questions independently using M5 history, including H4 veto, H1 value model, sweep freshness, session profiles, M5 confirmation, R:R, costs and multi-period stability.

See `docs/RESEARCH_V3.md`.

### v2 Pine — TradingView reference

Use:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

This remains a heavier `strategy()` reference for the v2-rule baseline. It provides:

```text
Strategy Tester
historical trade replay
rolling last-100 audit
win rate / expectancy / PF / max DD
```

It is useful for checking TradingView-side behavior, but it is not the current product version.

## 9. Why Python research cannot simply use all TradingView data automatically

TradingView supplies data to Pine inside TradingView, but it does not expose the user's entire private chart feed as a normal GitHub/Python database endpoint.

Therefore:

```text
live chart -> TradingView data automatically
research   -> independent data/xauusd_m5.csv
```

Once the M5 dataset is present, GitHub Actions can run the v3 research automatically.

## 10. Recommended workflow

```text
Day-to-day:
XAUUSD M15 + v3 FAST + AUTO

When a setup fires:
TradingView -> Vercel -> email

Research:
GitHub/Python v3 research engine

Cross-check:
v2 Pine Strategy Tester over matching historical periods
```

For the complete rule rationale see `docs/STRATEGY_V3.md`.

> Research software only. Historical performance does not guarantee future results.
