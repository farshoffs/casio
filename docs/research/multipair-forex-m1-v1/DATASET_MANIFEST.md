# FxPro M1 Multi-Pair Dataset Manifest

Date received: 2026-09-24

These user-supplied files are the working source for CASIO multi-pair research.

GitHub's normal contents API cannot store the raw files because each individual CSV is >100 MB. This manifest records exact fingerprints, coverage and schema so the source files can be verified byte-for-byte outside GitHub.

| Pair | File | Rows | Coverage UTC | Bytes | SHA-256 |
|---|---|---:|---|---:|---|
| EURUSD | fxpro_EURUSD_m1.csv | 3,584,839 | 2017-01-01 22:05 → 2026-09-24 15:38 | 328,629,225 | 733470dfc42b5babe806ab2e3308b07a9c244f7dec6d7ced2006dc95c4898c06 |
| GBPUSD | fxpro_gbpusd_m1.csv | 3,589,010 | 2017-01-01 22:05 → 2026-09-24 15:19 | 328,268,468 | f47e8218a4d00aaae65f3d7496dcf40638f5efacc47417a8c21b103d5c9b831c |
| GBPJPY | fxpro_GBPJPY_m1.csv | 3,606,586 | 2017-01-01 22:13 → 2026-09-24 15:32 | 347,702,708 | fd845d8cf5226019fc5a9e30dd345bf0017b6c90ceae72b705a2970058c548e1 |

Schema for all three:
`time_utc, open, high, low, close, tick_volume, symbol, timeframe`

Integrity checks:
- timeframe is M1 throughout;
- expected symbol only in each file;
- no consecutive duplicate timestamps found;
- no invalid OHLC envelope rows found;
- rows are chronological.

Research target requested:
- start RM100
- risk 5% current equity per entry
- minimum RR 1:3
- target WR 70%
- causal multi-timeframe execution where applicable
- real stop only; no protected/B.E. stop manipulation unless explicitly changed later
