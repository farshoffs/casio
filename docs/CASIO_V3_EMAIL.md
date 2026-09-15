# CASIO v3 Email Alerts — TradingView Free setup

The current setup uses TradingView Free without alert/webhook automation, so CASIO email alerts do **not** depend on TradingView.

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
CASIO v3
v2 MTF core + adaptive 24h session overlay
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

The existing standalone Apps Script project uses:

```text
apps-script/Code.gs
```

Initial setup:

```text
setupCasio()
sendTestEmail()
```

Default recipient:

```text
farhanshoffi@moe.gov.my
```

## 2. Web App deployment

```text
Deploy
-> Web app
-> Execute as: Me
-> Who has access: Anyone
```

`printWebhookUrl()` returns the private URL containing the CASIO token.

Do not commit that URL into source control.

## 3. GitHub Actions secret

Repository secret:

```text
CASIO_GAS_WEBHOOK_URL
```

Value:

```text
the complete private URL returned by printWebhookUrl()
```

The current workflow has already been designed to read only this secret for email delivery.

## 4. Live signal schedule

Workflow:

```text
.github/workflows/live-signal.yml
```

Scheduled minutes:

```text
02, 17, 32, 47 each hour
```

Each run:

```text
fetch recent Dukascopy M5
-> rebuild H4/H1/M15/M5 context
-> classify ASIA / LONDON / NEW YORK / TRANSITION
-> route SCALPING or INTRADAY
-> apply session-specific gates
-> reject stale/invalid setup
-> create casio.tv.v3 only for fresh valid LONG/SHORT
```

No valid setup means no email.

## 5. Session-aware signal fields

The v3 live payload now includes:

```text
session
playbook
session_policy
required_score
required_rr
```

Typical `playbook` values:

```text
RANGE_MEAN_REVERSION
PRIMARY_INTRADAY
ASIA_TREND_EXCEPTION
TRANSITION_TREND_EXCEPTION
```

The current Apps Script email already displays the session, mode, score, entry, stop, target, R:R, H4/H1 bias and M15 ADX. Extra session-aware fields are retained in the payload for logging/auditing even if the current email template does not render every field.

## 6. Session rules used by the live email engine

```text
London / New York Intraday
score >= 80
usable R:R >= 2.5

Asia directional exception
H1 aligned
score >= 90
usable R:R >= 3.0

Transition directional exception
H1 aligned
M15 ADX >= 25
score >= 90
usable R:R >= 3.0

Scalping
range-regime driven across sessions
```

These are current live rules, not claims that every session is profitable. The research engine compares them against the older `primary_only` policy.

## 7. Freshness and deduplication

GitHub scheduled jobs can start late. `casio/live_signal.py` rejects a setup older than the configured freshness limit rather than sending an obsolete entry.

Apps Script deduplicates repeated trade events using bar time, mode, direction and entry, so reruns of the same setup should not create repeated emails during the cache window.

## 8. TradingView setup

Normal visual setup:

```text
XAUUSD
M15
pine/CASIO_XAUUSD_v3_FAST.pine
AUTO
ADAPTIVE_24H
```

No TradingView `Create Alert` step is required.

## 9. Vercel

The existing Vercel `api/tradingview.py` receiver remains for webhook compatibility and future integrations, but it is not in the critical Free-plan email path.

Current critical path:

```text
GitHub Actions -> Apps Script -> email
```

## 10. Market data

Persistent research history is maintained separately by:

```text
.github/workflows/market-data-sync.yml
```

which maintains:

```text
data/xauusd_m5.csv
```

The live signal workflow fetches recent bars independently, so it does not need to wait for the daily persistent-data commit.

## 11. Security

Keep `CASIO_GAS_WEBHOOK_URL` only in GitHub Actions Secrets. Anyone with the complete URL may be able to submit payloads to the Apps Script endpoint, so rotate the Apps Script token if it is exposed.

Do not place the secret in Pine, Markdown, workflow YAML or normal repository variables.
