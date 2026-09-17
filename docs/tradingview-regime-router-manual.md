# CASIO Regime Router — TradingView Manual

This manual is for `tradingview/casio_regime_router_dashboard_v1.pine` (v1.1).

## What this script is

The script is a TradingView **strategy**, not a manual trading panel. It has two operating modes:

- **BACKTEST** — TradingView automatically creates simulated entries and exits so you can use Strategy Tester.
- **LIVE SIGNALS** — no simulated strategy orders are placed; the dashboard, chart levels, and alerts stay active for live monitoring.

The intended chart is **XAUUSD, 15 minute**. M15 creates the setup. Completed H1 and H4 candles provide higher-timeframe context.

## First setup

1. Open an XAUUSD chart in TradingView.
2. Set the chart timeframe to **15m**.
3. Open Pine Editor and paste/save `casio_regime_router_dashboard_v1.pine`.
4. Add it to the chart.
5. Open the script settings.
6. Under **00 · Mode / Backtest**, keep `Mode = BACKTEST` while testing.
7. Choose the backtest start and end dates.
8. Keep `Risk % of current equity = 5` for the CASIO research method.
9. Open **Strategy Tester** at the bottom of TradingView.

You do **not** need to click TradingView's `Trade` button or place a broker/manual trade. The strategy places simulated historical orders itself in BACKTEST mode.

## Reproducing the CASIO-style test

For a calendar-year test, use a fresh test window for that year. Example for 2026:

- Backtest start: `2026-01-01 00:00 UTC`
- Backtest end: `2026-12-31 23:59 UTC` (or the last date available on the feed)
- Initial capital: **100 MYR**
- Risk: **5% of current strategy equity**
- Commission: the script uses **0.005% per order side**, approximately 1 bp round trip
- Pyramiding: disabled
- One portfolio position at a time

The script calculates quantity from the stop distance so the intended loss at the stop is approximately 5% of current equity. It converts account-currency risk into the symbol currency before sizing.

TradingView results will not match the Python/Dukascopy research figures exactly because your TradingView XAUUSD provider, spread/bid-ask construction, OHLC bars, and broker emulator can differ.

## Dashboard reading

### Header

- `M15 · BACKTEST` — script is in simulated historical-order mode.
- `M15 · LIVE` — dashboard/alert mode; no simulated strategy entries are created.
- `USE M15` — wrong chart timeframe.

### Market State

- **H1** — completed H1 directional bias.
- **H4** — completed H4 directional bias plus H4 ADX.
- **TREND** — H1/H4 align and H4 ADX meets the router threshold.
- **MIXED** — the market does not meet the strong-trend definition.

### Technique rows

The five engines remain visible independently:

- `0591 MTF` — momentum/expansion continuation.
- `V1 Legacy` — M15 trend breakout.
- `Outcome First` — structural FVG/sweep or displacement setup.
- `Struct Portfolio` — structural portfolio with MTF context.
- `Struct Frequency` — looser structural continuation engine.

`LONG`, `SHORT`, or `WAIT` shows what each module is doing on the current M15 bar. `TARGET` shows its current 2R/3R/4R objective when a setup is active.

### Agreement

`▲ n` and `▼ n` count techniques that produced recent long/short evidence inside the router's recent M15 support window.

### Portfolio

This is the router's final action after applying regime-dependent priority. It shows:

- final direction,
- selected technique,
- selected R target.

If it says **WAIT**, there is no routed portfolio entry now.

### Levels

When a portfolio signal is accepted, the dashboard and chart show:

- **ENTRY** — estimated signal entry, then the actual Strategy Tester fill once filled.
- **SL** — stop-loss price.
- **TP** — target price derived from the selected 2R/3R/4R objective.

The chart draws three horizontal levels:

- white dashed = entry,
- red = stop loss,
- green = take profit.

By default the most recent levels remain visible after an exit so you can review the setup. Disable `Keep last trade levels after exit` if you want them removed when the trade closes.

## Backtest controls

The final dashboard row no longer displays RM100/equity. It displays:

- current mode,
- risk percentage,
- whether the current chart bar is inside the selected backtest range.

The equity curve and account results belong in **Strategy Tester**, where TradingView already provides the full trade list and performance view.

## Why Strategy Tester may show no trades

Check these in order:

1. `Mode` must be **BACKTEST**.
2. Chart must be **15m** if `Require chart timeframe = 15m` is enabled.
3. Your backtest start/end range must overlap loaded chart history.
4. The symbol must have enough earlier history for EMA/ATR/H1/H4 warm-up.
5. The risk-distance filters may reject unusually tight or unusually wide stops.
6. Use **Strategy Tester**, not TradingView's broker `Trade` panel.

If signals are visible as labels but Strategy Tester still shows no orders, check the mode/date-range row in the dashboard first.

## Live signals

When you are finished backtesting:

1. Change `Mode` to **LIVE SIGNALS**.
2. Leave the chart on XAUUSD M15.
3. Turn on `Emit JSON alert() on new portfolio signal`.
4. Create a TradingView alert using **Any alert() function call**.
5. Use the Vercel webhook URL as the TradingView webhook URL once the webhook deployment is connected.

The JSON contains direction, selected technique, router mode, estimated entry, SL, TP, target R, H1/H4 context, and risk percentage.

## What the TradingView backtest does and does not prove

This TradingView strategy is the operational/dashboard implementation of the Regime Router logic. It is useful for visual validation and TradingView Strategy Tester results, but it is a separate test environment from our Python/Dukascopy engine. Differences in feed and fill mechanics should be investigated rather than force-fitted until both platforms print the same number.
