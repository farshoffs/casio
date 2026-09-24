# CASIO Hybrid Core v1 — Validation Status

**Status: REJECTED FOR PRODUCTION after independent-feed validation (2026-09-24).**

Frozen v1 performed well on the recent independent Dukascopy M5 window but failed the older independent OctaFX M5 history.

- Dukascopy 2025-06-23 -> 2026-09-16: 366 trades, +68.90R after 1bp, PF 1.264.
- OctaFX 2017-2025 complete years: 1,735 trades in those full years, only 4/9 positive years; full validation slice 2016-07 -> 2026-01: 1,766 trades, -20.72R after 1bp, PF 0.985, RM100@1% -> RM62.23, 56.23% max DD.
- OctaFX gross before costs is only +58R / PF 1.044, so friction is not the only problem.
- No v1 thresholds should be retuned to rescue this failure.

Authoritative validation report is on branch `research/casio-hybrid-core-v1-validation`:
`reports/casio-hybrid-core-v1-independent/INDEPENDENT_VALIDATION.md`.
