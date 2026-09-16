# CASIO v4 Confluence Signal Engine

Status: **research challenger**. It does not replace CASIO v3 production automation until validation clears the acceptance gates.

## Objective

CASIO v4 is designed for XAUUSD M5 with an aggressive research objective:

- approximately 8 completed trades per week,
- approximately 70% profitable trades,
- positive expectancy after realistic execution costs,
- one position at a time,
- visible historical BUY/SELL signals with Entry, SL and TP on the TradingView chart.

Those numbers are **acceptance targets, not guaranteed outputs**. The Pine dashboard and the Python research harness display measured historical results rather than manufacturing the requested headline numbers.

## Trading logic

The engine routes four complementary setup families through one confluence score and structural risk gate.

### 1. Liquidity + FVG / displacement

A recent internal or external liquidity sweep must be followed by M5 displacement. A fair-value gap is rewarded in the confluence score but displacement above/below M5 value can also qualify, which keeps the setup usable when a literal three-candle FVG is absent.

### 2. Breakout retest

Price must close through a meaningful recent M5 range boundary, then retest and reclaim/reject that level within a limited bar window. H1/M15 context must not strongly oppose the trade.

### 3. BBMA re-entry

The model uses Bollinger Bands plus weighted MA5 high/low and EMA20/EMA50 context. It looks for a recent outer-band extreme followed by a re-entry/continuation candle in the direction allowed by H1 and M15.

### 4. Supply / demand rejection

Confirmed causal M5 pivots become the latest supply/demand references. A setup needs a rejection close near the zone plus supporting liquidity or BBMA context. Pivots are only usable after the right-hand confirmation bars exist, so historical signals do not use future information.

## Non-repainting context

H4, H1 and M15 context uses the previous **closed** higher-timeframe candle only. The M5 signal itself is accepted only on a confirmed M5 bar. This is deliberate: a historical marker must represent a signal that could actually have existed at that bar close.

## Risk and trade management

The initial SL is structural: recent M5 swing extreme plus an ATR buffer. Candidate trades are rejected when the SL distance is too small or too large relative to ATR.

The default challenger uses a relatively compact TP and optional breakeven protection because the requested 70% hit-rate / 8-trades-per-week objective is a different optimization problem from the older CASIO structural portfolio, which targeted fewer trades and much larger R winners.

The original SL remains the signal-time risk level shown in the alert. If breakeven protection triggers later, the active chart SL can move toward entry.

## TradingView

Use:

```text
pine/CASIO_XAUUSD_v4_CONFLUENCE.pine
```

Recommended chart:

```text
Symbol: XAUUSD
Timeframe: 5 minutes
Profile: QUALITY_70
```

The script is intentionally a TradingView `strategy()` rather than a plain `indicator()`. That gives the same on-chart BUY/SELL behavior while also retaining technique-generated historical entries/exits and exposing Strategy Tester statistics.

Historical plan segments can show Entry, initial SL and TP for prior accepted signals. The dashboard shows actual closed trades, historical win rate, profit factor and the current week's accepted-trade count.

## Alerts -> Vercel -> Google Apps Script

The v4 Pine script deliberately emits the existing `casio.tv.v3` JSON schema. That makes it backward-compatible with the current CASIO relay:

```text
TradingView alert()
  -> Vercel /api/tradingview.py
  -> validation + authentication
  -> Google Apps Script relay
  -> queued CASIO signal email
```

No v4-only backend migration is required for the initial test. The v4 playbook name is placed in `audit_status`, which the existing Apps Script email template already displays.

For a TradingView account with webhook support, create an alert using **Any alert() function call** and point it at the existing authenticated CASIO Vercel TradingView endpoint. Do not put webhook tokens in the Pine source or commit them to GitHub.

If using CASIO's current TradingView-Free workflow, keep v3 production automation active while v4 is evaluated visually and through GitHub research. A later promotion can mirror the frozen v4 rules into the Python live-signal job.

## Research harness

Run:

```bash
python -m casio.v4_confluence_research \
  --data data/xauusd_m5_dukascopy_research.csv \
  --output reports/v4-confluence
```

The bounded grid varies only a small set of execution parameters:

- minimum score,
- TP in R,
- breakeven trigger,
- cooldown.

It reserves the latest 30% of initialized data as chronological validation and ranks candidates using validation frequency, win rate, expectancy, PF and stability. Stop/TP collisions inside one M5 candle are treated conservatively as stop-first.

Outputs:

```text
reports/v4-confluence/LATEST.md
reports/v4-confluence/latest.json
reports/v4-confluence/candidate_grid.csv
```

The 8/week and 70% figures are only considered cleared when the chronological validation slice reaches both while maintaining positive expectancy. A candidate should still be checked against another feed/window before production promotion.
