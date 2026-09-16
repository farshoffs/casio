# Dukascopy XAUUSD M5 research base

This is a **separate research copy** of Dukascopy XAUUSD M5 BID data.

- CSV: `data/xauusd_m5_dukascopy_research.csv`
- Source: Dukascopy XAUUSD M5 BID via `scripts/fetch_dukascopy.mjs`
- Purpose: fast current-to-backwards research
- Backfill direction: **latest market first, then progressively backwards**
- Current target history floor: 2024-01-01 UTC
- Canonical live/email file remains `data/xauusd_m5.csv`
- The research copy must not overwrite or be merged into the canonical file.

Important: although the **download/backfill direction** is latest -> backwards, rows inside the CSV remain sorted in normal chronological order (oldest -> newest). CASIO feature engineering and replay code require monotonic chronological input.

The dedicated GitHub Actions workflow seeds the newest ~180 days first, then prepends older ~180-day slices until 2024 is covered. After that it keeps the latest end refreshed while accelerator runs become no-ops.
