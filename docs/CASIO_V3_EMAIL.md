# CASIO v3 — TradingView -> Vercel -> Google Apps Script

The current backend now handles **two** TradingView event streams:

```text
1. CASIO v3 trade signals
TradingView XAUUSD M15
        | casio.tv.v3
        v
Vercel /api/tradingview
        v
Google Apps Script
        v
farhanshoffi@moe.gov.my

2. CASIO M5 market data
TradingView XAUUSD M5
        | casio.market.v1
        v
Vercel /api/tradingview
        v
Google Apps Script
        v
CASIO XAUUSD M5 Data (Google Sheet)
```

The live product is **CASIO v3**, currently using the v2 regime-first MTF rule baseline. TradingView should call Vercel, not Apps Script directly.

## 1. Live signal alert

Use:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
XAUUSD
M15
AUTO
```

Create an alert:

```text
Condition: CASIO XAUUSD v3 FAST — Live MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook URL with its TradingView->Vercel token.

Only confirmed LONG/SHORT setups send signal alerts; `WAIT` does not send an email.

## 2. Automatic M5 market-data alert

Use the additional lightweight collector:

```text
pine/CASIO_XAUUSD_M5_FEED.pine
```

Open the **same XAUUSD feed on 5 minutes**, add the collector and create one alert:

```text
Condition: CASIO XAUUSD M5 DATA FEED
Trigger: Any alert() function call
Webhook URL: same CASIO Vercel webhook
```

After creation, TradingView sends every newly closed M5 bar on its servers. Your browser does not need to stay open.

The collector emits:

```text
schema = casio.market.v1
event = bar
symbol / ticker / timeframe / bar_time
open / high / low / close / volume
```

It is realtime-forward collection only; Pine alerts do not replay old historical bars.

## 3. Google Apps Script

Create or update the standalone Apps Script project with the latest:

```text
apps-script/Code.gs
```

Then run:

```text
setupCasio()
```

Approve the requested Mail and Spreadsheet permissions.

`setupCasio()` now configures:

```text
CASIO_EMAIL
CASIO_TOKEN
CASIO_MARKET_SHEET_ID
```

and creates a Google Spreadsheet named:

```text
CASIO XAUUSD M5 Data
```

with a sheet named `XAUUSD_M5`.

Recipient defaults to:

```text
farhanshoffi@moe.gov.my
```

Run `sendTestEmail()` to verify email delivery.

## 4. Deploy Apps Script

```text
Deploy
-> New deployment
-> Web app
-> Execute as: Me
-> Who has access: Anyone
-> Deploy
```

If this project was already deployed before the market-data changes, **update/redeploy the Web App to the new code version**.

After deployment run:

```text
printWebhookUrl()
```

Keep the printed token private.

## 5. Vercel environment variables

Production project:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=<private Apps Script token>
```

The TradingView->Vercel authentication token is separate.

The Python entrypoint remains:

```toml
[tool.vercel]
entrypoint = "api/tradingview:handler"
```

With GitHub connected to Vercel, current backend code changes should deploy from `main`; environment-variable changes still require a production redeploy.

## 6. Current schema support

Vercel accepts:

```text
casio.tv.v1
casio.tv.v2
casio.tv.v3
casio.market.v1
```

Apps Script actively handles:

```text
casio.tv.v2   signal email compatibility
casio.tv.v3   current signal email
casio.market.v1   M5 Google Sheet storage
```

## 7. Market CSV export

Vercel proxies the Apps Script market sheet as public market-only CSV:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?export=m5
```

The Apps Script token is inserted server-side by Vercel and is not exposed to the CSV consumer.

The returned columns are:

```csv
timestamp,open,high,low,close,volume
```

GitHub workflow `.github/workflows/market-data-sync.yml` downloads this CSV daily and merges it into `data/xauusd_m5.csv`.

## 8. Signal email queue and deduplication

For trade signals Apps Script:

- validates schema and XAUUSD,
- deduplicates repeated signal events,
- queues accepted signals,
- schedules email processing,
- sends through `MailApp`.

For market bars it:

- requires XAUUSD M5,
- rejects invalid OHLC,
- ignores duplicate/stale bar timestamps,
- appends accepted bars to the Google Sheet.

## 9. Health check

GET:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview
```

Expected fields include:

```json
{
  "ok": true,
  "service": "casio-tradingview",
  "email_relay_configured": true,
  "market_csv_export": true
}
```

If relay/export is false, check `CASIO_GAS_WEBAPP_URL` and `CASIO_GAS_TOKEN`, then redeploy Production.

## 10. Recreate TradingView alerts after Pine changes

TradingView alerts are stored snapshots. If either alert-producing Pine script changes, delete and recreate the affected alert from the latest script.

Updating GitHub alone does not replace an existing TradingView alert snapshot.

## 11. Security

- Do not commit plain webhook tokens to GitHub.
- Do not put the Apps Script secret inside Pine JSON.
- Keep authenticated webhook URLs private.
- The public `?export=m5` endpoint intentionally exposes only XAUUSD OHLC market data.
- Rotate a secret if it is accidentally exposed.
