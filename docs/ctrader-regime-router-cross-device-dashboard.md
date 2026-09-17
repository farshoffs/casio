# CASIO Regime Router — cross-device cTrader dashboard

Source:

`ctrader-web-plugin/regime-router-dashboard/index.html`

## Why this version

This is a **web-based cTrader plugin**, not a Desktop-only chart control.

cTrader web-based plugins can run in supported UI placements on:

- cTrader Mobile
- cTrader Web
- cTrader Windows
- cTrader Mac

The plugin connects to the active cTrader session through the cTrader Plugin SDK. It does not need a separate Open API login or token.

## What the dashboard shows

- Portfolio: LONG / SHORT / WAIT
- Selected Regime Router technique
- TREND / MIXED router mode
- H1 bias
- H4 bias and H4 ADX
- Five technique states:
  - M15-0591 MTF
  - V1 Legacy M15
  - Outcome First M15
  - Structural Portfolio MTF
  - Structural Frequency M15
- 30-minute technique agreement
- Live FxPro bid / ask
- Estimated Entry / SL / TP
- 2R / 3R / 4R target quality
- Timestamp of the latest completed M15 candle

## Data model

The dashboard requests the active account's XAUUSD/Gold data directly through the cTrader Plugin SDK:

- M15: 1000 bars
- H1: 500 bars
- H4: 500 bars
- D1: 100 bars

Only completed bars are used by the router calculations.

The dashboard refreshes the full router state after a new M15 boundary and also has a five-minute fallback refresh. Bid/ask values update from cTrader quote events.

## Router rules

The web dashboard ports the same current CASIO five-technique Regime Router structure used by the cTrader signal cBot:

Trend priority:

```text
M15-0591 MTF
→ V1 Legacy M15
→ Outcome First M15
→ Structural Portfolio MTF
→ Structural Frequency M15
```

Mixed priority:

```text
Structural Portfolio MTF
→ Outcome First M15
→ Structural Frequency M15
→ M15-0591 MTF
→ V1 Legacy M15
```

In mixed mode, M15-0591 and V1 require at least one additional agreeing technique inside the two-M15-bar agreement window.

The H4 strong-trend threshold remains ADX 18.

## Important source-of-truth note

This dashboard is read-only and independently reconstructs the router from cTrader historical bars and live quotes.

The **CASIO cTrader signal cBot remains the live signal source of truth**, because that cBot also maintains its own virtual-position state between signals. The web dashboard does not place trades and does not alter the signal cBot.

If a side-by-side test shows any router-state mismatch, use the cBot state and report the timestamp so the JavaScript port can be aligned.

## Hosting

A web-based cTrader plugin needs an HTTPS website URL.

The source is a single self-contained `index.html`, so it can be hosted as a static site on:

- Vercel
- GitHub Pages
- Cloudflare Pages
- any other HTTPS static host

No backend is required for the dashboard itself.

## Build the cTrader plugin

After the page is hosted:

1. Open cTrader Web, Windows or Mac while signed into your cTID.
2. Open the Plugins area and create/build a **web-based plugin**.
3. Use the hosted URL of `index.html`.
4. Name it something like **CASIO Regime Router**.
5. Enable placements you want on desktop/web and the supported Mobile placement.
6. Enable the plugin.

Once the web-based plugin is associated with your cTID and cloud synchronisation is enabled, cTrader can make the supported plugin available across your cTrader apps.

## First test

Open the plugin on the FxPro account.

Expected status flow:

```text
Connecting
→ Connected
→ Updating
→ Live
```

The footer should identify the FxPro XAUUSD/Gold symbol cTrader returned and report how many M15 bars were loaded.

If the account's gold symbol is not exactly `XAUUSD`, the dashboard searches for:

1. exact `XAUUSD`
2. a symbol name containing `XAUUSD`
3. a symbol whose name/description contains `Gold`

## Read-only safety

The dashboard imports only data/quote SDK methods. It does not import or call order-creation, order-modification or position-closing methods.
