# CASIO v2 — MTF + Google Apps Script Email Alerts

This guide covers the current live alert path for `pine/CASIO_XAUUSD_v2_MTF.pine`.

## Architecture

```text
TradingView XAUUSD M15
        |
        | confirmed casio.tv.v2 alert JSON
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

TradingView should point to **Vercel**, not directly to Apps Script. Vercel is the fast, stable webhook front door; Apps Script handles email delivery behind it.

## 1. Use CASIO v2 in TradingView

Open:

```text
XAUUSD
15 minute chart
```

Paste:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

into Pine Editor, save, and **Add to chart**.

Recommended operating mode:

```text
Strategy mode: AUTO
```

CASIO v2 internally reads:

```text
H4  directional bias
H1  structure, value, liquidity and range regime
M15 liquidity sweep, BOS and execution
M5  scalping confirmation
```

Do not switch chart timeframe just to feed those timeframes; they are already requested internally. The strategy is designed to execute on M15.

## 2. What produces an email

Email is sent only when CASIO produces a confirmed trade setup. `WAIT` states do not send trade emails.

### Intraday

A simplified eligible setup is:

```text
H4 directional bias
-> H1 does not veto the direction
-> H1 value/pullback location
-> recent M15 liquidity sweep
-> M15 BOS/confirmation
-> London or New York session
-> >= 1:2.5 usable R:R before opposing H1 liquidity
-> score threshold
-> signal
```

Preferred target is about 1:3, but the target is constrained by nearer H1 opposing liquidity.

### Scalping

```text
H1 compressed/ranging
-> M15 low-ADX compressed range
-> M15 range-edge sweep + reclaim
-> M5 rejection confirmation
-> >= 1:1.3 to range mean
-> score threshold
-> signal
```

Scalping is therefore a separate mean-reversion playbook, not a smaller Intraday trade.

## 3. Create the Google Apps Script

1. Open `script.google.com` using the Google account that can send email to `farhanshoffi@moe.gov.my`.
2. Create a standalone project named **CASIO Email Alerts**.
3. Replace its `Code.gs` with the repository file:

```text
apps-script/Code.gs
```

4. Run `setupCasio()` once.
5. Approve the requested permissions.
6. Run `sendTestEmail()`.
7. Confirm the test reaches:

```text
farhanshoffi@moe.gov.my
```

`setupCasio()` stores the recipient and creates a private `CASIO_TOKEN` in Script Properties.

## 4. Deploy Apps Script as a Web App

Use:

```text
Deploy
-> New deployment
-> Type: Web app
-> Execute as: Me
-> Who has access: Anyone
-> Deploy
```

If your Google Workspace policy does not allow `Anyone`, an external webhook cannot call the Web App. In that case the Workspace policy must be changed or a Google account that permits public Web App deployment must be used.

After deployment, run:

```text
printWebhookUrl()
```

It prints a URL similar to:

```text
https://script.google.com/macros/s/DEPLOYMENT_ID/exec?token=LONG_PRIVATE_TOKEN
```

Keep the token private.

## 5. Configure Vercel

The repository contains:

```text
api/tradingview.py
pyproject.toml
```

`pyproject.toml` defines the Python entrypoint required by Vercel:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

In the Vercel project connected to `farshoffs/casio`, add these **Production** environment variables:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=THE_PRIVATE_TOKEN_CREATED_BY_setupCasio
```

Do not append `?token=...` to `CASIO_GAS_WEBAPP_URL`; Vercel adds `CASIO_GAS_TOKEN` when relaying.

Redeploy Production after adding or changing environment variables.

### TradingView -> Vercel authentication

The TradingView-facing webhook is separately protected by the CASIO webhook token. Do not confuse it with the Apps Script token.

Conceptually:

```text
TradingView token  -> protects TradingView -> Vercel
Apps Script token  -> protects Vercel -> Apps Script
```

## 6. Check Vercel health

A GET request to:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview
```

returns service information including whether the Apps Script relay is configured.

Expected conceptually:

```json
{
  "ok": true,
  "service": "casio-tradingview",
  "schemas": ["casio.tv.v1", "casio.tv.v2"],
  "email_relay_configured": true
}
```

If `email_relay_configured` is `false`, recheck the two Production environment variables and redeploy.

## 7. Create/re-create the TradingView alert

With v2 attached to the XAUUSD M15 chart:

```text
Create Alert
Condition: CASIO XAUUSD v2 — Regime-First MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing Vercel webhook URL:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?token=<TRADINGVIEW_TO_VERCEL_TOKEN>
```

Do **not** paste the Apps Script URL into TradingView.

Important: TradingView alerts contain a compiled snapshot of the strategy. If the Pine alert logic changes, delete/recreate the TradingView alert after updating the script.

## 8. Signal payload and email contents

CASIO v2 sends a `casio.tv.v2` payload with the confirmed setup and relevant current performance context.

The email can contain:

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
rolling win rate
expectancy
profit factor
audit status
TradingView bar time in Malaysia time
```

The score is a setup-quality score, not a guaranteed win probability.

## 9. Deduplication and queued delivery

Apps Script deduplicates repeated alerts using the setup identity so the same bar/setup does not generate repeated emails.

The Web App queues email work and returns quickly. A short-lived Apps Script trigger then sends the message through `MailApp`. This reduces the chance of webhook processing being delayed by email delivery.

## 10. Testing order

Use this order so each layer is tested independently:

```text
A. Apps Script: run setupCasio()
B. Apps Script: run sendTestEmail() -> email arrives
C. Apps Script: deploy Web App + run printWebhookUrl()
D. Vercel: set CASIO_GAS_WEBAPP_URL + CASIO_GAS_TOKEN
E. Vercel: redeploy Production
F. Vercel GET /api/tradingview -> email_relay_configured: true
G. TradingView: add latest v2 Pine script
H. TradingView: recreate alert using Vercel webhook URL
I. Confirmed CASIO setup -> Vercel -> Apps Script -> email
```

## 11. Troubleshooting

### Test email works, but TradingView email does not

Check:

```text
Vercel environment variables
Production redeployment after env changes
TradingView alert webhook URL
TradingView alert is using latest v2 script snapshot
Vercel runtime logs for CASIO_SIGNAL / relay failures
```

### Vercel reports Python entrypoint missing

Make sure `pyproject.toml` is present at repository root with:

```toml
[tool.vercel]
entrypoint = "api.tradingview:handler"
```

### Apps Script cannot be public

If Workspace policy does not permit `Who has access: Anyone`, the relay cannot invoke the Web App anonymously. This is an account policy issue, not a Pine issue.

### Duplicate emails

The Apps Script already includes deduplication. If duplicates still appear, inspect whether multiple TradingView alerts were created for the same strategy/chart.

## 12. v1 vs v2

Keep v1 only as a research comparison baseline.

For v2, compare in TradingView Strategy Tester:

```text
trade count
net profit / return
profit factor
average trade / expectancy
maximum drawdown
Intraday results
Scalping results
stability across different date ranges
```

Do not select a version from win rate alone.

See `docs/STRATEGY.md` for the complete strategy rationale and `docs/TRADINGVIEW.md` for normal TradingView operation.
