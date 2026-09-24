# Rule Extraction Schema

Use this template for every setup or technique taught in the playlist.

## 1. Context

- Instrument(s):
- Higher-timeframe bias:
- Mid-timeframe structure:
- Entry timeframe:
- Session/time window:
- News/event filter:
- Market regime:

## 2. Indicators / chart objects

For every indicator or drawing:
- exact name,
- parameters,
- price source,
- timeframe,
- purpose,
- whether it is mandatory or confirmatory.

## 3. Setup prerequisites

Write only boolean or numeric conditions where possible.

Example format:

```text
HTF bullish = H1 close > defined structure level
MTF pullback = M15 trades into defined zone
LTF trigger = M5 closes above trigger candle high
```

Any phrase such as “strong”, “clean”, “good momentum”, “rejection”, “respect”, or “liquidity” must be either:
1. defined objectively from the source, or
2. tagged HYPOTHESIS and converted into testable variants.

## 4. Entry

Record:
- market/limit/stop entry,
- exact trigger,
- entry timing relative to candle close,
- whether multiple entries are allowed,
- expiry/cancellation logic,
- same-bar ambiguity rules.

## 5. Stop loss

Record:
- anchor,
- buffer,
- minimum/maximum distance,
- structural invalidation,
- whether the source ever moves SL.

CASIO adaptation must keep a real fixed SL for the user's current tests. Any creator BE/trailing/protected-SL logic must be stored separately and must not be silently used in fixed-SL backtests.

## 6. Take profit

Record:
- fixed R,
- structural target,
- partial exits,
- runner logic,
- target hierarchy.

For current CASIO acceptance tests, normalize the final evaluation to fixed 1:3 R:R unless a separate experiment is explicitly requested.

## 7. Invalidation / no-trade conditions

Examples:
- HTF disagreement,
- wrong session,
- no displacement,
- target blocked,
- excessive spread/volatility,
- trigger too late,
- setup stale.

## 8. Multi-timeframe dependency

Describe the exact information flow:

```text
HTF context -> MTF setup location/structure -> LTF confirmation -> execution
```

No higher-timeframe value may use an unclosed future bar.

## 9. Source evidence

For each atomic rule:

| Rule ID | Rule | Evidence timestamp | Tag | Confidence |
|---|---|---|---|---|
| R001 | pending | pending | DIRECT | pending |

## 10. Testable variants

When the source is vague, generate bounded alternatives instead of guessing one interpretation.

Example:
- rejection wick >= 0.5 ATR,
- rejection wick >= 1.0 ATR,
- close back inside zone,
- close beyond trigger candle.

All such variants remain HYPOTHESIS until tested.
