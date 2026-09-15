# CASIO v2 — MTF + Google Apps Script Email Alerts

## Architecture

```text
TradingView XAUUSD M15
        |
        | CASIO v2 alert() JSON
        v
Vercel /api/tradingview
        |
        | validated CASIO v2 signal
        v
Google Apps Script Web App
        |
        | queued MailApp delivery
        v
farhanshoffi@moe.gov.my
```

TradingView should point to Vercel, not directly to Apps Script. Google Apps Script ContentService responses are redirected; Vercel absorbs that behavior and gives TradingView a clean, fast webhook response.

## 1. Add CASIO v2 to TradingView

Open XAUUSD on **15 minutes**.

Paste this GitHub file into Pine Editor:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Save and **Add to chart**.

Recommended initial setting:

```text
Strategy mode: AUTO
```

CASIO v2 internally reads:

- H4 — directional bias
- H1 — structure, value location and range regime
- M15 — liquidity sweep, BOS and main chart execution
- M5 — range/scalping rejection confirmation

### Intraday engine

```text
H4 directional bias
 -> H1 must not veto direction
 -> H1 value/pullback location
 -> recent M15 liquidity sweep
 -> M15 BOS/confirmation
 -> London or New York window
 -> >= 1:2.5 room before opposing H1 liquidity
 -> signal
```

Preferred target is 1:3, but CASIO will not target through nearer opposing H1 liquidity. It requires at least 1:2.5 available room.

### Scalping engine

```text
H1 compressed/ranging
 -> M15 low-ADX compressed range
 -> M15 sweep of range edge
 -> M5 rejection confirmation
 -> >= 1:1.3 to range mean
 -> scalp signal
```

This keeps scalping as a separate mean-reversion strategy rather than a smaller version of the intraday engine.

## 2. Create the Google Apps Script

1. Open `script.google.com` using the Google account that can send mail to `farhanshoffi@moe.gov.my`.
2. Create a new standalone Apps Script project named **CASIO Email Alerts**.
3. Replace `Code.gs` with:

```text
apps-script/Code.gs
```

4. Run `setupCasio()` once.
5. Approve the requested permissions.
6. Run `sendTestEmail()` and confirm the test reaches `farhanshoffi@moe.gov.my`.

`setupCasio()` automatically creates a private `CASIO_TOKEN` in Script Properties and sets the recipient email.

## 3. Deploy Apps Script as a Web App

Apps Script:

```text
Deploy
 -> New deployment
 -> Type: Web app
 -> Execute as: Me
 -> Who has access: Anyone
 -> Deploy
```

If your Google Workspace administrator does not allow `Anyone`, the external webhook relay cannot invoke the script; an account/admin policy change or another Google account capable of public Web App deployment is required.

After deployment, run:

```text
printWebhookUrl()
```

The execution log prints a URL similar to:

```text
https://script.google.com/macros/s/DEPLOYMENT_ID/exec?token=LONG_PRIVATE_TOKEN
```

Keep this URL private.

## 4. Configure Vercel environment variables

In the Vercel project connected to `farshoffs/casio`, add these **Production** environment variables:

```text
CASIO_GAS_WEBAPP_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
CASIO_GAS_TOKEN=THE_TOKEN_PRINTED_BY_setupCasio
```

Do not include `?token=...` in `CASIO_GAS_WEBAPP_URL`; keep the token in `CASIO_GAS_TOKEN`.

Redeploy Production after adding/changing environment variables.

The existing TradingView -> Vercel token can remain unchanged.

## 5. Create/re-create the TradingView alert

Any time Pine alert logic changes, recreate the TradingView alert so TradingView uses the latest compiled script snapshot.

With CASIO v2 on the XAUUSD M15 chart:

```text
Create Alert
Condition: CASIO XAUUSD v2 — Regime-First MTF
Trigger: alert() function calls only
Webhook URL: ON
```

Use the existing CASIO Vercel webhook:

```text
https://casio-farhan-shoffis-projects.vercel.app/api/tradingview?token=<YOUR_EXISTING_CASIO_TOKEN>
```

Do **not** use the Apps Script URL in TradingView.

## 6. Signal email

A confirmed signal email contains:

- LONG / SHORT
- Intraday / Scalping
- market regime
- London / New York / off-session context
- setup score
- entry
- stop
- target
- R:R
- H4 bias
- H1 bias
- M15 ADX
- rolling win rate
- expectancy
- profit factor
- audit health
- Malaysian timestamp

The Apps Script queues email work before returning, then a time trigger sends it through `MailApp` so webhook handling stays fast.

## 7. Testing order

Use this order to isolate problems quickly:

```text
A. Apps Script sendTestEmail() -> email arrives
B. Vercel GET /api/tradingview -> email_relay_configured: true
C. TradingView alert -> Vercel webhook status successful
D. Real CASIO setup -> email arrives
```

## 8. v1 vs v2

Keep v1 temporarily for comparison. In TradingView Strategy Tester compare:

- net profit
- profit factor
- max drawdown
- number of trades
- average trade
- Intraday vs Scalping behavior

Do not decide from win rate alone. The v2 goal is better expectancy and drawdown behavior through regime selection and higher-timeframe vetoes.
