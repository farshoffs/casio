# Reverse-All FxPro M1 v1 — Frozen Scope

Date: 2026-09-25

## Goal

Retest the documented CASIO technique families with trade direction reversed on the original **FxPro M1** source data for:

- EURUSD
- GBPUSD
- GBPJPY
- XAUUSD

Primary experiment rule:

> Keep the setup detector and structural levels unchanged; flip LONG <-> SHORT at the accepted-signal boundary, then rebuild the real stop/3R target on the reversed side.

Common execution standard for cross-strategy comparison:

- RM100 start
- 5% current-equity risk
- fixed 3R target
- real SL only
- no BE / protected-stop conversion
- one active position per strategy/pair
- causal MTF reconstruction from M1
- M1 chronology for SL/TP
- same-M1 SL/TP collision = SL
- headline results gross; cost sensitivity reported separately
- no Dukascopy substitution

## Strategy families in the reverse sweep

The scope is the full family set documented in `research/multipair-forex-m1-v1`:

1. EMA Ribbon Break
2. Donchian-10 D1/H4 breakout
3. Tick-volume momentum continuation
4. ADX/DI momentum rotation
5. CASIO NY Precision v1 transfer
6. NY opening-hour precision transfer
7. BBMA Reentry MTF
8. ICT pre-NY liquidity sweep -> MSS/FVG retrace
9. Silver Bullet 10:00-11:00 New York
10. London/Asia sweep -> MSS/FVG retrace
11. Previous-day high/low sweep -> MSS/FVG retrace
12. Pure S&D first retest + lower-TF confirmation
13. Naked S/R rejection/reversal + lower-TF confirmation
14. Bermula Accurate-Fast transfer
15. FiboRSI8 20/80
16. FiboRSI8 23/77 + HTF 32.5/67.5
17. Bounded MTF deep-retracement precision candidate

The XAUUSD pass will additionally include the documented strict ICT MTF practical model as a separate row so its direction-flip behavior is not hidden inside the looser ICT family.

## Required raw data

The prior research manifest confirms these exact three files existed:

| Pair | File | Rows | Coverage UTC | SHA-256 |
|---|---|---:|---|---|
| EURUSD | `fxpro_EURUSD_m1.csv` | 3,584,839 | 2017-01-01 22:05 -> 2026-09-24 15:38 | `733470dfc42b5babe806ab2e3308b07a9c244f7dec6d7ced2006dc95c4898c06` |
| GBPUSD | `fxpro_gbpusd_m1.csv` | 3,589,010 | 2017-01-01 22:05 -> 2026-09-24 15:19 | `f47e8218a4d00aaae65f3d7496dcf40638f5efacc47417a8c21b103d5c9b831c` |
| GBPJPY | `fxpro_GBPJPY_m1.csv` | 3,606,586 | 2017-01-01 22:13 -> 2026-09-24 15:32 | `fd845d8cf5226019fc5a9e30dd345bf0017b6c90ceae72b705a2970058c548e1` |

Full-history XAUUSD FxPro M1 was used by the ICT research, with coverage through 2026-09-24, but the raw file was not committed because of size.

## Data-recovery audit

Current persistent sources were checked before creating this branch.

- GitHub contains the manifests/reports, not the >100 MB raw EURUSD/GBPUSD/GBPJPY CSVs.
- The personal Library currently contains a small `fxpro_XAUUSD_mn1.csv`, but it has only 2,780 M1 rows covering 2026-09-23 to 2026-09-25, so it is not the historical source.
- The Library also contains `archive.zip` with `XAU_1m_data.csv` (2004-06-11 to 2026-01-30), but its broker/feed identity is not proven to be FxPro, so it is explicitly excluded from this test.
- No Dukascopy data may be used as a fallback.

The reverse sweep must not run until the original FxPro M1 bytes are reattached or otherwise made accessible.
