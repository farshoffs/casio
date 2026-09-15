# CASIO v3 Email Alerts — TradingView Free setup

The current user has a TradingView Free account without alert/webhook automation. Therefore CASIO email alerts do **not** depend on TradingView.

Current path:

```text
Dukascopy XAUUSD M5
        |
        v
GitHub Actions
.github/workflows/live-signal.yml
        |
        v
casio/live_signal.py
        |
        v
CASIO v3 / v2-rule baseline
        |
        +-- WAIT -> no email
        |
        +-- fresh LONG / SHORT
                |
                v
        Google Apps Script
                |
                v
       farhanshoffi@moe.gov.my
```

TradingView remains the visual chart/dashboard only.

## 1. Google Apps Script

Create or update a standalone Apps Script project with:

```text
apps-script/Code.gs
```

Run:

```text
setupCasio()
```

Approve permissions, then run:

```text
sendTestEmail()
```

The default recipient is:

```text
farhanshoffi@moe.gov.my
```

## 2. Deploy Apps Script as a Web App

```text
Deploy
-> New deployment
-> Web app
-> Execute as: Me
-> Who has access: Anyone
-> Deploy
```

If your Google Workspace policy blocks public Web Apps, the GitHub runner cannot call it until that policy restriction is resolved or the script is deployed from a suitable account.

After deployment run:

```text
printWebhookUrl()
```

It returns a private URL containing the CASIO token, conceptually:

```text
https://script.google.com/macros/s/DEPLOYMENT_ID/exec?token=PRIVATE_TOKEN
```

Do not commit this URL into GitHub source code.

## 3. Add the one GitHub Actions secret

Open the `farshoffs/casio` repository:

```text
Settings
-> Secrets and variables
-> Actions
-> New repository secret
```

Name:

```text
CASIO_GAS_WEBHOOK_URL
```

Value:

```text
the complete private URL returned by printWebhookUrl()
```

This is the only secret required by the current free live-email workflow.

## 4. Live signal schedule

Workflow:

```text
.github/workflows/live-signal.yml
```

Scheduled minutes:

```text
02, 17, 32, 47 each hour
```

The small offset gives the latest M15 candle time to close and the data source time to publish the bar.

Each run fetches recent XAUUSD M5 data, rebuilds the H4/H1/M15/M5 context, evaluates the same CASIO v3/v2-rule baseline and creates a `casio.tv.v3` payload only for a fresh valid setup.

If there is no setup, nothing is emailed.

If GitHub starts the scheduled job too late, `casio/live_signal.py` rejects a setup older than its configured freshness limit instead of sending an obsolete entry.

## 5. Email contents

The Apps Script formatter includes fields such as:

```text
LONG / SHORT
INTRADAY / SCALPING
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
bar time
```

The v3 score is setup confluence, not a statistically calibrated probability of winning.

## 6. Deduplication

Apps Script deduplicates repeated trade events using signal details including bar time, mode, direction and entry. Therefore reruns of the same M15 setup should not create repeated emails during the cache window.

## 7. TradingView does not need an alert

Your normal TradingView setup remains:

```text
XAUUSD
M15
pine/CASIO_XAUUSD_v3_FAST.pine
AUTO
```

No TradingView Create Alert step is required for this architecture.

The optional files/API routes that support TradingView webhooks are retained for compatibility with accounts that have alert features, but they are not required for the current setup.

## 8. Vercel is no longer in the critical email path

The existing Vercel `api/tradingview.py` receiver remains useful for webhook compatibility and future integrations, but the Free-plan live signal workflow sends its valid signal directly from GitHub Actions to Google Apps Script.

This removes the need for TradingView -> Vercel webhook triggering.

## 9. Market data

Historical and recent automation data comes from Dukascopy. The persistent research dataset is maintained separately by:

```text
.github/workflows/market-data-sync.yml
```

which updates:

```text
data/xauusd_m5.csv
```

The live signal workflow fetches recent bars independently so it does not need to wait for the daily persistent-data commit.

## 10. Security

Keep `CASIO_GAS_WEBHOOK_URL` only in GitHub Actions Secrets. Anyone with that full URL may be able to submit payloads to the Apps Script endpoint, so rotate the Apps Script token if the URL is exposed.

Do not put the secret in Pine, README files, workflow YAML or normal repository variables.
