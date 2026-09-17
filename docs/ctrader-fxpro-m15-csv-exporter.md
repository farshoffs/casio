# CASIO FxPro XAUUSD M15 CSV Exporter

Source: `ctrader/CasioFxProM15CsvExporter.cs`

This cBot is **data-only**. It never places trades.

## What it does

- Requests **M15** bars directly from the cTrader/FxPro feed.
- Loads older history back to the configured UTC start date, subject to the history FxPro exposes.
- Writes **closed candles only**.
- Resumes an existing CSV without duplicating already-written timestamps.
- Appends each newly closed M15 candle while the local cBot is running.

CSV columns:

```text
time_utc,open,high,low,close,tick_volume,symbol,timeframe
```

Example:

```text
2026-09-18T06:45:00Z,3645.100,3649.200,3641.550,3647.800,1254,XAUUSD,M15
```

## Install in cTrader Desktop

1. Open **cTrader Desktop → Algo**.
2. Create a new C# cBot named **CasioFxProM15CsvExporter**.
3. Delete the template and paste the complete contents of `ctrader/CasioFxProM15CsvExporter.cs`.
4. Build it.
5. Add a **Local** instance to FxPro **XAUUSD** and start it.

The chart itself can be any timeframe because the exporter explicitly requests M15 data internally. Using an XAUUSD M15 chart is still the clearest setup.

## Recommended parameters

- **Start Date UTC:** `2024-01-01` (change this if you want older history)
- **Max History Loads:** `500`
- **Rebuild CSV On Start:** `false`
- **CSV File Name:** `fxpro_xauusd_m15.csv`
- **Append New M15 Bars:** `true`
- **Require XAUUSD:** `true`

On the first run, the cBot loads history back to the requested date and exports it. On later runs, it reads the last timestamp already present and resumes from there.

If you change the start date to an earlier date and want the CSV rebuilt from that earlier point, set **Rebuild CSV On Start = true** for one run. This deletes the existing exporter CSV and rebuilds it from the configured start date. Set it back to `false` afterward.

## Where the CSV is saved

With `AccessRights.None`, cTrader's restricted file API stores the file under the cBot's own data directory:

```text
Documents/cAlgo/Data/cBots/CasioFxProM15CsvExporter/fxpro_xauusd_m15.csv
```

The cBot also prints the file name, earliest loaded bar and latest written bar in the Algo log.

## Almost-live collection

Keep the exporter running as a **Local** cBot. Whenever an M15 candle closes, the cBot appends one row to the CSV. That means the CSV advances once every 15 minutes during active XAUUSD trading.

The live row is taken from cTrader's `BarClosed` event, so the exporter does not write the still-forming candle.

## Cloud vs Local

Use **Local** for this CSV collector. The point of this cBot is to create a persistent file that you can access on your PC. Keep the separate CASIO signal cBot in Cloud if you want 24/7 signals without leaving the PC on.

## Notes

- `tick_volume` is cTrader tick volume, not exchange volume.
- The amount of historical data available is controlled by FxPro/cTrader. The log reports the earliest M15 bar the server exposes.
- The exporter uses UTC timestamps.
- If FxPro uses a non-standard gold symbol name that does not contain `XAUUSD`, set **Require XAUUSD = false** after verifying you attached the cBot to the correct gold symbol.
