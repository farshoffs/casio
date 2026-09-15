# CASIO v3 Email Alerts — TradingView -> Vercel -> Google Apps Script

The current live path is:

```text
TradingView XAUUSD M15
        |
        | casio.tv.v3 signal
        v
Vercel /api/tradingview
        |
        | validate + log + relay
        v
Google Apps Script Web App
        |
        | queued MailApp delivery
        v
farhanshoffi@moe.gov.my
```

The live product is **CASIO v3**. It currently uses the v2 regime-first MTF rule baseline.

TradingView should call Vercel, not Apps Script directly.

## 1. TradingView

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

Use the existing CASIO Vercel webhook URL with its existing TradingView->Vercel token.

Do not place the Apps Script token in the Pine JSON body.

## 2. What creates an email

Only a confirmed LONG/SHORT setup calls `alert()`.

A normal `WAIT` dashboard state does not send an email.

v3 signal data includes:

```text
schema = casio.tv.v3
symbol / ticker / timeframe / bar_time
mode
regime
session
direction
score
entry
stop
target
rr
h4_bias
h1_bias
m15_adx
```

The lightweight v3 FAST indicator intentionally avoids the heavy historical rolling-audit calculations of the old v2 Pine strategy.

## 3. Google Apps Script

Create a standalone Apps Script project named something like:

```text
CASIO Email Alerts
```

Replace its `Code.gs` with:

```text
apps-script/Code.gs
```

Then run:

```text
setupCasio()
```

Approve the required permissions.

The setup function stores:

```text
CASIO_EMAIL
CASIO_TOKEN
```

in Script Properties.

Recipient defaults to:

```text
farhanshoffi@moe.gov.my
```

Run:

```text
sendTestEmail()
```

and confirm the message arrives.

## 4. Deploy Apps Script

Use:

```text
Deploy
-> New deployment
-> Web app
-> Execute as: Me
-> Who has access: Anyone
-> Deploy
```

If Google Workspace policy prevents a public Web App, Vercel cannot invoke it until the account/admin restriction is changed or another suitable account is used.

After deployment, run:

```text
printWebhookUrl()
```

Keep the printed token private.

## 5. Vercel environment variables

In the production `casio` Vercel project configure:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=<private Apps Script token>
```

Do not append the token to `CASIO_GAS_WEBAPP_URL`; keep it in the separate environment variable.

The TradingView->Vercel authentication token is a different secret.

Redeploy Production after changing environment variables.

## 6. Vercel Python entrypoint

The repo root contains:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

This resolves the Python function entrypoint for `api/tradingview.py`.

## 7. Schema compatibility

The Vercel receiver currently accepts:

```text
casio.tv.v1
casio.tv.v2
casio.tv.v3
```

The Apps Script formatter accepts:

```text
casio.tv.v2
casio.tv.v3
```

Current live alerts should use `casio.tv.v3`.

## 8. Email queue and deduplication

Apps Script:

- rejects unsupported payloads,
- deduplicates repeated signal events,
- queues accepted signals,
- schedules email processing,
- sends through `MailApp`.

The queue keeps webhook handling quick instead of making TradingView wait for synchronous email delivery.

## 9. Health check

GET:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview
```

The response should conceptually include:

```json
{
  "ok": true,
  "service": "casio-tradingview",
  "schemas": ["casio.tv.v1", "casio.tv.v2", "casio.tv.v3"],
  "email_relay_configured": true
}
```

If `email_relay_configured` is false, check the two `CASIO_GAS_*` environment variables and redeploy.

## 10. Recreate TradingView alerts after Pine changes

TradingView stores a snapshot of the Pine script when an alert is created.

Therefore after alert-producing Pine changes:

```text
delete old alert
save/add latest v3 FAST script
create the alert again
```

Updating GitHub alone does not replace an already-running TradingView alert snapshot.

## 11. Security notes

- Do not commit plain webhook tokens to GitHub.
- Do not put the Apps Script secret in Pine alert JSON.
- Treat webhook URLs containing authentication tokens as secrets.
- Rotate a token if it is accidentally exposed.
