# CASIO Email Alerts

The current product is **CASIO v3**. The up-to-date email setup is:

```text
docs/CASIO_V3_EMAIL.md
```

Read [`CASIO_V3_EMAIL.md`](CASIO_V3_EMAIL.md) for the current flow:

```text
TradingView v3 FAST
-> Vercel /api/tradingview
-> Google Apps Script
-> farhanshoffi@moe.gov.my
```

The Vercel backend still accepts `casio.tv.v2` for compatibility with the historical v2 Pine research strategy, but new live alerts should use `casio.tv.v3`.

This file is retained as a compatibility pointer so old links do not break.
