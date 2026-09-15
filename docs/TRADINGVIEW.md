# CASIO + TradingView

CASIO can now run directly on TradingView as a Pine Script strategy and emit live XAUUSD setup alerts to a CASIO webhook endpoint.

## 1. Add the CASIO Pine strategy

Open TradingView and select an **XAUUSD** chart. Start with **15 minute (M15)**.

Open **Pine Editor**, paste the contents of:

```text
pine/CASIO_XAUUSD_v1.pine
```

Save it and choose **Add to chart**.

Recommended first settings:

```text
Strategy mode: AUTO
Intraday minimum score: 70
Intraday target RR: 3.0
Scalping minimum score: 68
Scalping target RR: 1.5
Maximum ADX: 22
Maximum range / ATR: 5.5
Range-edge fraction: 0.22
Emit alert() JSON: ON
```

AUTO means:

```text
ADX <= 22 AND 30-bar range <= 5.5 ATR -> SCALPING
otherwise                                -> INTRADAY
```

The chart dashboard shows the active mode, ADX, current score, signal state and detected regime.

## 2. TradingView Strategy Tester

Because the Pine file is a `strategy()`, TradingView's **Strategy Tester** will show historical trades from the chart's own data.

Use it as a visual/independent reference. CASIO's Python audit remains the canonical rolling-last-100-trades research engine because its simulator has its own conservative execution assumptions.

## 3. Deploy the CASIO webhook

The repository includes a Vercel-compatible Python function:

```text
api/tradingview.py
```

Deploy the repository to Vercel, then configure an environment variable:

```text
CASIO_WEBHOOK_TOKEN=<a long random token>
```

The resulting endpoint is:

```text
https://YOUR-CASIO-DOMAIN.vercel.app/api/tradingview?token=YOUR_TOKEN
```

Do not put the token inside the Pine alert JSON. Keep it in the webhook URL configured in TradingView.

A GET request to `/api/tradingview` returns a simple health response.

The receiver currently validates and normalizes the live signal then writes it to Vercel runtime logs with the prefix:

```text
CASIO_SIGNAL
```

The next CASIO layer can persist these normalized signals into a database/dashboard without changing the TradingView payload contract.

## 4. Create the TradingView alert

With **CASIO XAUUSD v1 — Intraday + Scalping** added to the chart:

1. Click **Create alert**.
2. For **Condition**, select the CASIO strategy.
3. Select **alert() function calls only**.
4. Enable **Webhook URL**.
5. Paste:

```text
https://YOUR-CASIO-DOMAIN.vercel.app/api/tradingview?token=YOUR_TOKEN
```

6. Create the alert.

The Pine strategy itself controls the alert frequency and only emits a setup on a confirmed bar close.

## 5. Payload

Example live webhook body:

```json
{
  "schema": "casio.tv.v1",
  "event": "signal",
  "symbol": "OANDA:XAUUSD",
  "ticker": "XAUUSD",
  "timeframe": "15",
  "bar_time": 1789472700000,
  "mode": "intraday",
  "direction": "long",
  "score": 85,
  "entry": 3675.20,
  "stop": 3668.40,
  "target": 3695.60,
  "rr": 3.0,
  "adx": 27.4,
  "atr": 6.18
}
```

## 6. How the two systems relate

```text
TradingView XAUUSD M15
        |
        +--> Pine strategy -> chart + Strategy Tester
        |
        +--> alert() JSON -> CASIO webhook -> live signal stream

Historical OHLC CSV
        |
        +--> Python CASIO -> rolling last 100 trades -> audit agent
```

The Pine and Python implementations intentionally use the same initial thresholds. When CASIO's audit recommends a researched parameter change, update both implementations in the same Git commit so live and historical logic stay versioned together.

## Notes

- CASIO is research software, not an auto-execution broker bot.
- Start with M15 XAUUSD.
- Use confirmed-bar alerts to avoid acting on an unfinished candle.
- A TradingView Strategy Tester result and the Python backtest can differ because execution simulators use different fill assumptions.
