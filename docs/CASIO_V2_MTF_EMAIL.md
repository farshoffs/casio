# CASIO Email Alerts — TradingView -> Vercel -> Google Apps Script

This guide covers the current email path. The preferred live TradingView script is now:

```text
pine/CASIO_XAUUSD_v3_FAST.pine
```

The full research/backtest strategy `pine/CASIO_XAUUSD_v2_MTF.pine` remains compatible with the same backend.

## Architecture

```text
TradingView XAUUSD M15
        |
        | casio.tv.v3 (FAST) or casio.tv.v2 (research) alert
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

TradingView should point to **Vercel**, not directly to Apps Script.

## 1. TradingView setup

For normal use:

```text
XAUUSD
15 minute chart
pine/CASIO_XAUUSD_v3_FAST.pine
Strategy mode: AUTO
```

Create an alert:

```text
Condition: CASIO XAUUSD v3 FAST — Live MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook URL.

If you are using the heavier v2 research strategy, the same backend still accepts `casio.tv.v2` alerts.

## 2. What produces an email

Only confirmed LONG/SHORT setups send alerts. `WAIT` states do not send trade emails.

The email includes current information such as:

```text
LONG / SHORT
Intraday / Scalping
regime
session
score
entry
stop
target
R:R
H4 bias
H1 bias
M15 ADX
```

v2 can additionally include rolling research statistics. v3 FAST intentionally omits heavy rolling-audit calculations from the live Pine script.

## 3. Create Google Apps Script

1. Open `script.google.com` with the Google account allowed to send mail.
2. Create a standalone project named **CASIO Email Alerts**.
3. Replace `Code.gs` with repository file `apps-script/Code.gs`.
4. Run `setupCasio()` once.
5. Approve permissions.
6. Run `sendTestEmail()`.
7. Confirm the test reaches:

```text
farhanshoffi@moe.gov.my
```

`setupCasio()` creates the private Apps Script token in Script Properties.

## 4. Deploy Apps Script as Web App

```text
Deploy
-> New deployment
-> Type: Web app
-> Execute as: Me
-> Who has access: Anyone
-> Deploy
```

If Workspace policy blocks public Web Apps, the external Vercel relay cannot call it until that policy/account restriction is resolved.

After deployment run:

```text
printWebhookUrl()
```

Keep the resulting token private.

## 5. Configure Vercel

The repo contains:

```text
api/tradingview.py
pyproject.toml
```

Vercel Python entrypoint:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

Production variables:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=THE_PRIVATE_TOKEN_CREATED_BY_setupCasio
```

The TradingView -> Vercel token is separate from the Vercel -> Apps Script token.

## 6. Backend schema support

Current Vercel receiver accepts:

```text
casio.tv.v1
casio.tv.v2
casio.tv.v3
```

Current Apps Script email receiver accepts:

```text
casio.tv.v2
casio.tv.v3
```

v1 is retained only for compatibility and is not relayed to the current email formatter.

## 7. Health check

GET:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview
```

Expected conceptually:

```json
{
  "ok": true,
  "service": "casio-tradingview",
  "schemas": ["casio.tv.v1", "casio.tv.v2", "casio.tv.v3"],
  "email_relay_configured": true
}
```

If `email_relay_configured` is false, recheck `CASIO_GAS_WEBAPP_URL` and `CASIO_GAS_TOKEN`, then redeploy Production.

## 8. Recreate alerts after Pine changes

TradingView alerts run from a stored snapshot of the script. When alert-producing Pine code changes:

```text
delete old alert
-> add/save latest Pine script
-> create a new alert
```

## 9. Recommended current split

```text
v3 FAST -> daily TradingView dashboard + live signals
v2 MTF  -> Strategy Tester + rolling research audit
Vercel  -> webhook validation/logging/background relay
Apps Script -> email delivery
```

This keeps the live TradingView panel lighter without giving up the heavier research tooling.
