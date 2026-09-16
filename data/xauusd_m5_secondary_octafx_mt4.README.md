# Secondary XAUUSD M5 base — OctaFX / Octa Markets MT4

This file is intentionally **separate** from `data/xauusd_m5.csv` and must never be merged into the canonical Dukascopy BID feed.

- File: `data/xauusd_m5_secondary_octafx_mt4.csv`
- Original file: `XAU_5m_data.csv`
- Original MD5: `7ec4a38929b4d4e845a1713dec022c85`
- Exact user-upload archive was cross-checked against the published mirror by MD5
- Original source described by the dataset author: Octa Markets / OctaFX MetaTrader 4 History Center
- Rows: 1,443,451 M5 bars
- Original broker-time coverage: 2004-06-11 07:15 through 2026-01-30 23:55
- Normalization: broker EET/EEST server time converted to UTC using `Europe/Helsinki`
- Purpose: independent secondary-feed robustness research and historical regime testing
- Not used for canonical live/email execution

Research policy: current Dukascopy remains the canonical execution feed. This secondary feed is a separate base used to check whether structural edges survive a different broker/data source.
