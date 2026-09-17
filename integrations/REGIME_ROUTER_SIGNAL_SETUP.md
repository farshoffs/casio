# CASIO Regime Router signal bridge

## Flow

TradingView `alert()` JSON -> Vercel `/api/signal` -> Google Apps Script Web App -> Google Sheet + optional email.

## 1. TradingView

Use `tradingview/casio_regime_router_dashboard_v1.pine` on XAUUSD M15.

Create an alert with condition **Any alert() function call**. Set the webhook URL to the deployed Vercel `/api/signal` endpoint. The Pine script generates the JSON payload itself.

If using a secret, set the Pine input `Webhook shared secret` to the same value as Vercel `SIGNAL_SECRET`.

## 2. Google Apps Script

1. Create a Google Sheet and copy its spreadsheet ID.
2. Create a standalone Apps Script project and paste `integrations/apps-script-regime-signal/Code.gs`.
3. In **Project Settings -> Script properties**, configure:
   - `SPREADSHEET_ID`: required.
   - `RELAY_SECRET`: recommended; must match Vercel `APPS_SCRIPT_RELAY_SECRET`.
   - `NOTIFY_EMAIL`: optional email destination.
4. Deploy as **Web app**.
5. Execute as yourself. Choose the access setting required for your account/workspace so Vercel can POST to it.
6. Copy the Web App execution URL ending in `/exec`.

`doPost` appends each accepted signal to a `Signals` sheet and stores the latest signal in Script Properties. `doGet` returns the latest signal as JSON.

## 3. Vercel

Deploy the directory `integrations/vercel-regime-signal` as the Vercel project root.

Environment variables:

- `SIGNAL_SECRET`: optional but recommended; must match the TradingView Pine input.
- `APPS_SCRIPT_WEBHOOK_URL`: Apps Script `/exec` URL.
- `APPS_SCRIPT_RELAY_SECRET`: must match Apps Script `RELAY_SECRET` when configured.

The endpoint is:

`POST /api/signal`

A `GET /api/signal` request is a simple health check.

The Vercel function validates and normalizes the TradingView payload, removes the TradingView secret, forwards the signal to Apps Script, and writes the normalized event to Vercel runtime logs.

## Notes

- TradingView webhooks are delivery notifications, not an order execution guarantee.
- The Pine strategy is a live/dashboard implementation of the frozen research logic. TradingView broker-emulator results can differ from the Python/Dukascopy research because of feed, fill, session and independent source-technique replay differences.
- Keep shared secrets out of public screenshots and published Pine source.
