# CASIO RR10 — cross-device cTrader plugin

## Purpose

This is the single cTrader dashboard for CASIO RR10 across:

- cTrader Mobile / iOS / Android
- cTrader Web
- cTrader Windows
- cTrader Mac

Hosted plugin URL:

`https://farshoffs.github.io/casio/`

Source:

- `ctrader-web-plugin/cross-device/index.html`
- `ctrader-web-plugin/regime-router-dashboard/index.html` is an exact alias so the old path cannot drift.

## Architecture

The plugin is intentionally a thin client.

It does **not** download historical trendbars and it does **not** implement RR10 routing logic in JavaScript.

Every confirmed M15 evaluation is performed by the canonical Python RR10 engine:

`casio/regime_router_engine.py`

The scheduled main-branch workflow fetches the current XAUUSD feed, evaluates RR10, builds:

`casio/rr10_dashboard_state.py`

and publishes one public, non-account-specific snapshot to:

`rr10-live-state/rr10-state.json`

The plugin fetches that exact state on every device. It uses the cTrader Plugin SDK only for an optional live XAUUSD bid/ask overlay. If the cTrader quote connection is unavailable, the shared RR10 state still displays.

## Why this replaced the old dashboard

The previous WebView requested historical trendbars from the cTrader host. On FxPro cTrader Desktop 5.9.16 those requests repeatedly timed out even after:

- moving from a compatibility wrapper to the official trendbar API,
- reducing to a single M15 stream,
- adding retries,
- paging history,
- increasing request timeouts.

The cross-device plugin removes that dependency completely.

## Data and integrity

The shared state includes:

- engine and state schema
- WAIT / LONG / SHORT portfolio state
- TREND / MIXED router mode
- H1 bias
- H4 bias and ADX
- fixed 3R target model
- fixed 5% research risk model
- active entry / stop / target when one RR10 trade is active
- completed M15 timestamp
- feed freshness / stale flag

The decision feed is currently the same rolling Dukascopy XAUUSD M5 -> M15 cloud feed used by the scheduled RR10 live pipeline. The live FxPro quote shown in the plugin is an execution-price overlay and is not substituted into the canonical decision state.

If the state feed is stale, the plugin visibly marks it stale and warns the user not to treat the displayed state as current.

## Install in cTrader

Create a **web-based / multi-platform plugin** from the hosted URL above in cTrader Web, Windows or Mac. Enable the desired desktop/web placement and the Mobile placement. Once associated with the same cTID and synchronised, open the plugin from cTrader Mobile on iOS/Android or from the laptop apps.

Expected build label:

`RR10-XD1`

Expected healthy status:

- State live
- Quote live (or Quote optional if the host quote connection is unavailable)

No cTrader historical-data request is required on iOS or desktop.
