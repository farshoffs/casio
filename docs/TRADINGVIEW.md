# CASIO v3 + TradingView

TradingView is the primary **live CASIO v3 interface**. The current v3 live strategy still uses the **v2 regime-first MTF rule baseline**.

CASIO separates fast live charting, automatic market-data collection and deeper research:

```text
TradingView v3 FAST -> current signal/dashboard
TradingView M5 feed -> automatic research bars
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

v3 FAST is an `indicator()` rather than a historical strategy simulator. It keeps the current MTF decision engine in TradingView while Vercel handles webhook/email/data relay and Python handles deeper independent research.

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

Short is the inverse. Preferred target is about 1:3, capped by nearer H1 opposing liquidity.

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

It also uses `calc_bars_count` budgets. Defaults:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

Changing TradingView chart timeframe still forces Pine recalculation. The intended workflow is simply to remain on M15.

## 5. v3 FAST dashboard

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

`WAIT` is a normal result. The score is not a win probability.

## 6. Live signal alert

After adding the latest v3 FAST script:

```text
Create Alert
Condition: CASIO XAUUSD v3 FAST — Live MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook. v3 emits schema `casio.tv.v3`.

Important: TradingView stores an alert snapshot. When alert-producing Pine logic changes, delete the old alert and create it again from the latest script.

## 7. Automatic M5 research-data collector

CASIO now has a second, tiny Pine script dedicated to data collection:

```text
pine/CASIO_XAUUSD_M5_FEED.pine
```

One-time TradingView setup:

```text
1. Open the SAME XAUUSD symbol/feed used by CASIO.
2. Change that chart to 5 minutes.
3. Paste CASIO_XAUUSD_M5_FEED.pine into Pine Editor.
4. Save + Add to chart.
5. Create Alert.
6. Condition: CASIO XAUUSD M5 DATA FEED.
7. Select: Any alert() function call.
8. Enable Webhook URL.
9. Use the same CASIO Vercel webhook URL used by the signal alert.
```

After that, TradingView sends one `casio.market.v1` JSON message after each newly closed M5 bar. TradingView alerts execute on TradingView servers, so your browser and chart do not need to remain open.

The storage path is:

```text
TradingView M5 alert
      -> Vercel
      -> Apps Script
      -> Google Sheet
      -> Vercel CSV proxy
      -> GitHub daily sync
      -> data/xauusd_m5.csv
      -> v3 research
```

### Historical limitation

Script alerts only trigger on realtime bars. The M5 feed therefore starts collecting **after the alert is created**; it does not replay old historical bars through the webhook.

For multi-year research you can still do a one-time TradingView M5 CSV export later. `casio/sync_market_data.py` merges and deduplicates the automatic realtime feed with any existing historical rows, so manual backfill and automatic collection can coexist.

## 8. Vercel + Apps Script path

The same backend handles both signal alerts and M5 bars:

```text
/api/tradingview
   |
   +-- casio.tv.v3      -> signal/email
   +-- casio.market.v1  -> M5 market-data storage
```

Apps Script creates/uses a Google Sheet named:

```text
CASIO XAUUSD M5 Data
```

The server-side market CSV proxy is:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?export=m5
```

This endpoint contains public XAUUSD OHLC data only. The private Apps Script token stays in Vercel environment variables.

See `docs/CASIO_V3_EMAIL.md` for Apps Script/Vercel deployment.

## 9. Automatic GitHub sync and research

`.github/workflows/market-data-sync.yml` runs daily at 21:20 UTC. It downloads the current stored M5 bars, merges them into `data/xauusd_m5.csv`, deduplicates timestamps and commits only when the dataset changed.

That data commit automatically triggers `.github/workflows/v3-research.yml`.

The v3 research workflow then tests the current strategy questions using the updated dataset. It also has a weekly scheduled safety run and manual dispatch.

## 10. Historical research references

### Python v3 research engine — primary automated research

```bash
python -m casio.research_cli \
  --data data/xauusd_m5.csv \
  --output reports/v3-research
```

It tests H4 veto, H1 value model, sweep freshness, sessions, M5 confirmation, R:R, costs and multi-period stability.

### v2 Pine — TradingView reference

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

The heavier `strategy()` remains the TradingView historical reference for the v2-rule baseline and provides Strategy Tester plus rolling last-100 metrics. It is not the current product version.

## 11. Recommended workflow

```text
Day-to-day trading:
XAUUSD M15 + v3 FAST + AUTO

Data collection:
XAUUSD M5 + M5 DATA FEED alert (runs server-side)

Signals:
TradingView -> Vercel -> Apps Script -> email

Dataset:
TradingView -> Apps Script Sheet -> GitHub daily CSV sync

Research:
GitHub/Python v3 robustness engine

Cross-check:
v2 Pine Strategy Tester over matching periods
```

For the complete rule rationale see `docs/STRATEGY_V3.md`; for research methodology see `docs/RESEARCH_V3.md`.

> Research software only. Historical performance does not guarantee future results.
