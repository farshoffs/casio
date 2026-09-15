# CASIO v3 + TradingView Free

TradingView is the primary **visual CASIO v3 interface**, but the current user setup is a **TradingView Free account without alert/webhook automation**.

Therefore the live architecture deliberately separates charting from automation:

```text
TradingView Free
  -> XAUUSD M15
  -> CASIO v3 FAST dashboard
  -> visual LONG / SHORT / WAIT context

Dukascopy + GitHub Actions
  -> current XAUUSD M5 data
  -> same CASIO v3/v2-rule baseline in Python
  -> automatic signal email
  -> independent research/backtest data
```

No TradingView alert is required.

## 1. Normal TradingView setup

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

v3 FAST is the day-to-day visual indicator. It reads H4/H1/M5 internally, so you normally remain on M15 rather than changing timeframes manually.

## 2. Timeframe hierarchy

```text
H4  -> directional context
H1  -> structure, value proxy, opposing liquidity, range regime
M15 -> main setup: sweep, BOS, session, levels
M5  -> Scalping confirmation only
```

The current product is **CASIO v3** and the current trading-rule baseline is the **v2 regime-first MTF rule set**.

## 3. AUTO routing

```text
H1 range regime + M15 range regime
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

## 4. v3 FAST dashboard

The panel shows:

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

`WAIT` is intentional. Score is setup confluence, not a calibrated win probability.

## 5. Why the dashboard may take time to load

Changing chart timeframe forces TradingView to recalculate Pine. v3 FAST is lighter than the old v2 strategy because it bundles H4/H1/M5 requests and limits requested MTF history.

Default request budgets:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

The intended workflow is to leave CASIO on XAUUSD M15.

## 6. Automatic email signals without TradingView alerts

The current Free-plan signal path is:

```text
Dukascopy XAUUSD M5
        |
        v
GitHub Actions
.github/workflows/live-signal.yml
        |
        v
casio/live_signal.py
        |
        v
same v3/v2-rule baseline
        |
        +-- no setup -> do nothing
        |
        +-- valid fresh setup
                |
                v
         Google Apps Script
                |
                v
       farhanshoffi@moe.gov.my
```

The job is scheduled at approximately:

```text
:02
:17
:32
:47
```

UTC minute positions each hour, just after M15 closes.

GitHub scheduled jobs are not a low-latency trading exchange. They can start late. CASIO therefore rejects a signal if the corresponding setup has become too stale rather than emailing an old entry.

## 7. Automatic research data

The research dataset is also independent of TradingView alerts:

```text
Dukascopy bid M5
-> daily GitHub sync
-> data/xauusd_m5.csv
-> CASIO v3 Research & Robustness
```

The first successful automatic sync backfills from 2020-01-09 UTC. Later runs fetch only a recent overlap and deduplicate it into the existing dataset.

This solves both the historical-backfill problem and the ongoing-data problem without requiring manual TradingView CSV downloads.

## 8. Feed differences

Your TradingView chart may use a different provider than Dukascopy. Gold/FX is not a single centralized exchange feed, so exact candles and therefore individual setup timing can differ slightly between providers.

Use TradingView as your visual execution/context screen, while treating the Python/Dukascopy engine as an independent automation and research implementation. We should validate broad parity before trusting exact trade-for-trade correspondence.

## 9. v2 Pine reference

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

This heavier `strategy()` remains a historical TradingView reference for the baseline rule family. It is useful for Strategy Tester/rolling audit where available, but it is not the current v3 product.

## 10. Optional TradingView alert collector

```text
pine/CASIO_XAUUSD_M5_FEED.pine
```

This file is retained for accounts that have TradingView alerts/webhooks. It is **not needed in the current Free-plan setup**.

## 11. Recommended current workflow

```text
Chart:
TradingView Free -> XAUUSD M15 -> v3 FAST -> AUTO

Automatic signal:
Dukascopy -> GitHub Actions -> Python v3 -> Apps Script -> email

Historical data:
Dukascopy -> daily GitHub sync -> data/xauusd_m5.csv

Research:
Python v3 robustness engine

Reference check:
v2 Pine Strategy Tester when useful/available
```

See `docs/CASIO_V3_EMAIL.md` for the one-time email-secret setup and `docs/RESEARCH_V3.md` for research methodology.

> Research software only. Historical performance does not guarantee future results.
