# CASIO v4 Confluence Signal Engine

Status: **research challenger**. It does not replace CASIO v3 production automation yet.

## Objective and current result

CASIO v4 is designed for XAUUSD M5 with these acceptance targets:

- at least about 8 completed trades per week,
- at least about 70% profitable trades,
- positive expectancy,
- one position at a time,
- visible historical BUY/SELL signals with Entry, SL and TP on TradingView.

The current validated-core configuration cleared the headline frequency and hit-rate gates on the chronological validation slice of the repository's Dukascopy M5 research data:

- 9.48 trades/week,
- 74.16% win rate,
- +0.032R mean expectancy per completed trade,
- 1.12 profit factor,
- 9.95R maximum closed-trade drawdown,
- 178 validation trades.

These are historical research measurements, not guaranteed future performance. The Python replay does not yet debit broker spread/slippage/commission explicitly, so the relatively small expectancy must be rechecked in TradingView with the intended XAUUSD feed and realistic execution costs before any production promotion.

## Validated default core

The strongest tested default is deliberately simpler than the initial four-entry-family version:

- BBMA re-entry: enabled as a standalone entry,
- supply/demand rejection: enabled as a standalone entry,
- liquidity sweep / FVG: retained as confluence but disabled as a standalone entry,
- breakout/retest: retained as confluence but disabled as a standalone entry,
- primary-session minimum score: 55,
- TP: 0.60R,
- breakeven trigger: 0.35R,
- breakeven lock: +0.05R,
- cooldown: 6 M5 bars,
- maximum accepted trades/day: 3.

Why: on the same validation slice, standalone breakout/retest reduced expectancy, while the BBMA + supply/demand core preserved more than 8 trades/week and improved the combined hit rate and profit factor.

## Signal logic

### BBMA re-entry

The model uses Bollinger Bands, weighted MA5 high/low, EMA20/EMA50 and higher-timeframe context. It looks for a recent outer-band extreme followed by re-entry/continuation in a direction allowed by H1/M15 context.

### Supply / demand rejection

Confirmed causal M5 pivots become the latest supply/demand references. A setup requires a rejection close near the level plus liquidity or BBMA support. A pivot only becomes available after its right-side confirmation bars exist, so historical signals do not use future information.

### Liquidity / FVG and breakout context

Liquidity sweeps, displacement, fair-value gaps and breakout/retest structures are still computed. They contribute to the direction-specific confluence score and can be switched back on as standalone entry families from the Pine inputs for research, but they are off by default in the validated core.

## Non-repainting context

H4, H1 and M15 context uses the previous **closed** higher-timeframe bar only. The M5 signal is accepted only after the M5 bar is confirmed. Historical markers therefore represent conditions that existed at that bar close rather than retrospective future-bar knowledge.

## Risk and management

The initial SL is structural: the recent M5 swing extreme plus an ATR buffer. Trades are rejected when the stop distance is outside the allowed ATR-normalized range.

The original SL is retained in the signal payload as the initial risk level. After entry, optional breakeven management can move the active stop toward entry when price reaches the configured R threshold.

## TradingView

Use:

```text
pine/CASIO_XAUUSD_v4_CONFLUENCE.pine
```

Recommended initial chart test:

```text
Symbol: XAUUSD
Timeframe: 5 minutes
Profile: FREQUENCY
TP: 0.60R
Breakeven trigger: 0.35R
Standalone entries: BBMA + supply/demand ON; liquidity/FVG + breakout OFF
```

The script is intentionally a TradingView `strategy()` rather than a plain `indicator()`. It still displays BUY/SELL signals but additionally keeps technique-generated historical trades and makes Strategy Tester statistics available.

Historical plan segments display Entry, initial SL and TP for accepted signals. The dashboard displays measured closed trades, historical win rate, profit factor and the current week's accepted-trade count.

## Alerts -> Vercel -> Google Apps Script

The v4 Pine script deliberately emits the existing `casio.tv.v3` JSON schema. It is therefore backward-compatible with the current CASIO relay:

```text
TradingView alert()
  -> Vercel /api/tradingview.py
  -> validation + authentication
  -> Google Apps Script relay
  -> queued CASIO signal email
```

No v4-only backend schema migration is required for the challenger test. The v4 playbook is placed in `audit_status`, which the existing Apps Script email template already displays.

For a TradingView account with webhook support, create an alert using **Any alert() function call** and use the existing authenticated CASIO Vercel TradingView endpoint. Keep tokens outside Pine/GitHub.

Keep v3 production automation active while v4 is evaluated. Production promotion should happen only after the Pine script compiles on TradingView and Strategy Tester results on the intended broker/feed remain positive after realistic commission, spread and slippage assumptions.

## Research harness

Main bounded research:

```bash
python -m casio.v4_confluence_research \
  --data data/xauusd_m5_dukascopy_research.csv \
  --output reports/v4-confluence
```

Fast profile validation:

```bash
python -m casio.v4_quick_validate \
  --data data/xauusd_m5_dukascopy_research.csv
```

Playbook diagnostics:

```bash
python -m casio.v4_edge_diagnose \
  --data data/xauusd_m5_dukascopy_research.csv
```

The research uses a chronological 70/30 split and conservative stop-first treatment when both SL and TP are touched within one M5 candle. See `reports/v4-confluence/VALIDATED_CORE.md` for the promoted challenger metrics.
