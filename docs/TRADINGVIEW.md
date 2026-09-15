# CASIO v3 + TradingView Free

TradingView is the primary **visual CASIO v3 interface**, while automation runs independently because the current setup uses **TradingView Free without alert/webhook automation**.

```text
TradingView Free
  -> XAUUSD M15
  -> CASIO v3 FAST dashboard
  -> visual LONG / SHORT / WAIT context

Dukascopy + GitHub Actions
  -> current XAUUSD M5 data
  -> CASIO v3 Python decision engine
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
Session policy: ADAPTIVE_24H
```

v3 FAST reads H4/H1/M5 internally, so you normally remain on M15 rather than switching timeframes manually.

## 2. Current rule family

CASIO v3 now means:

```text
v2 regime-first MTF core
+
v3 adaptive 24h session overlay
```

Timeframe roles:

```text
H4  -> directional context
H1  -> bias, value proxy, opposing liquidity, range regime
M15 -> main setup: sweep, BOS, session, levels
M5  -> Scalping confirmation
```

## 3. AUTO routing

```text
H1 range regime + M15 range regime
        |
        +--> true  -> SCALPING
        +--> false -> INTRADAY
```

The session overlay then controls how strict Intraday must be.

## 4. Session-aware behavior

UTC session buckets:

```text
ASIA        00:00-06:00
LONDON      07:00-11:00
NEW YORK    12:30-16:30
TRANSITION  everything else
```

### London / New York

Normal Intraday directional rules:

```text
H4 aligned
H1 not strongly opposite
H1 value condition
recent M15 sweep
M15 BOS
usable R:R >= 2.5
score >= 80
```

### Asia

If the market is ranging, AUTO still prefers Scalping.

A directional Asia Intraday trade is an exception and requires:

```text
H1 aligned with the trade
usable R:R >= 3.0
score >= 90
```

plus the normal H4/value/sweep/BOS gates.

### Transition

Directional Transition trades are even more selective:

```text
H1 aligned
M15 ADX >= 25
usable R:R >= 3.0
score >= 90
```

### Scalping

Scalping remains available across sessions whenever the H1+M15 range regime, edge sweep, M5 confirmation and range-mean R:R all qualify.

## 5. Dashboard

The current v3 FAST panel shows:

```text
STATUS
MODE
REGIME
H4 / H1 BIAS
SESSION
SESSION RULE
ADX / SCORE
SIGNAL
ENTRY
STOP
TARGET
R:R
H1 RANGE
ENGINE
```

`SESSION RULE` shows the active minimum score/R:R for Intraday, or `RANGE PLAYBOOK` when AUTO has selected Scalping.

`WAIT` is intentional. Score is setup confluence, not a calibrated win probability.

## 6. Why the dashboard may take time to load

Changing chart timeframe forces TradingView to recalculate Pine and its external timeframe requests.

v3 FAST is lighter than the old v2 strategy because it bundles H4/H1/M5 requests and limits requested MTF history.

Default request budgets:

```text
H4: 300 bars
H1: 500 bars
M5: 1500 bars
```

The intended workflow is to leave CASIO on XAUUSD M15.

## 7. Automatic email signals without TradingView alerts

The Free-plan signal path is:

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
CASIO v3 adaptive 24h rules
        |
        +-- no setup -> do nothing
        |
        +-- fresh valid setup
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

just after each M15 close.

The payload includes:

```text
session
playbook
session_policy
required_score
required_rr
```

so an emailed Asia or Transition setup can be distinguished from a normal London/New York setup.

GitHub scheduled jobs can start late, so CASIO rejects stale setups rather than emailing a very old entry.

## 8. Automatic research data

```text
Dukascopy bid M5
-> GitHub data sync/backfill
-> data/xauusd_m5.csv
-> CASIO v3 Research & Robustness
```

The historical sync is configured to backfill from 2020-01-09 UTC and then maintain a recent overlap. Historical downloads are chunked and paced to reduce provider-rate-limit problems.

## 9. Feed differences

Your TradingView chart may use a different provider than Dukascopy. XAUUSD is not represented by one universal candle feed across every broker/provider.

Therefore:

```text
TradingView -> visual context
Python/Dukascopy -> automation + research
```

The two should express the same strategy family, but exact candle values and individual signal timing can differ.

## 10. v2 Pine reference

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

v2 remains useful as a historical reference for the original MTF core. It does **not** contain the new adaptive 24h session overlay, so it is no longer a full 1:1 historical reference for current v3 entry gating.

## 11. Optional TradingView alerts

`CASIO_XAUUSD_v3_FAST.pine` still contains optional `alert()` JSON for accounts that support alerts, and `pine/CASIO_XAUUSD_M5_FEED.pine` remains as an optional collector.

Neither is required for the current Free-plan automation.

## 12. Recommended workflow

```text
Chart:
TradingView Free -> XAUUSD M15 -> v3 FAST -> AUTO -> ADAPTIVE_24H

Automatic signal:
Dukascopy -> GitHub Actions -> Python v3 -> Apps Script -> email

Historical data:
Dukascopy -> GitHub sync -> data/xauusd_m5.csv

Research:
Python v3 robustness engine + per-session analysis

Reference:
v2 Pine for the original core only
```

See `docs/STRATEGY_V3.md` for rule rationale, `docs/CASIO_V3_EMAIL.md` for email setup, and `docs/RESEARCH_V3.md` for research methodology.

> Research software only. Historical performance does not guarantee future results.
