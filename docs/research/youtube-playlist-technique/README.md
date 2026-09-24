# YouTube Playlist Technique Research

Source playlist:
- https://youtube.com/playlist?list=PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O
- Playlist ID: `PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O`

## Mission

Learn the complete technique from the playlist, preserve the creator's actual rules, convert discretionary ideas into explicit machine-testable conditions, and test only after evidence extraction is complete.

This research is isolated from the live/main CASIO strategy. Nothing in this branch should be promoted to `main` merely because it sounds plausible.

## Evidence states

Every rule must be tagged as one of:

- `DIRECT` — explicitly taught or demonstrated in the source.
- `DERIVED` — logically inferred from multiple direct examples.
- `HYPOTHESIS` — our proposed operationalization of vague/discretionary language.
- `TESTED` — implemented and evaluated against market data.

Never silently upgrade a HYPOTHESIS into a creator rule.

## Current CASIO test gate

Unless the user changes it later:

- Instrument: XAUUSD.
- Multi-timeframe logic is mandatory.
- New York session only, DST-aware.
- Starting equity: RM100.
- Risk: 5% of current equity per trade.
- Fixed take-profit: 1:3 R:R.
- Real stop-loss only; no break-even/protected-stop accounting.
- Target win-rate band: 60%–80%.
- Minimum frequency: 8 trades per month.

These are CASIO evaluation constraints, not necessarily rules taught in the playlist.

## Research files

- `SOURCE_INDEX.md` — source/video inventory and ingestion status.
- `RULE_EXTRACTION.md` — canonical schema for turning lessons into objective rules.
- `AGENT_RESEARCH_PLAN.md` — repeatable AI-agent research loop.
- `STATUS.md` — current progress, blockers, and next executable actions.

## Promotion rule

A candidate technique is eligible for implementation only when:
1. its source evidence is traceable,
2. entry/SL/TP/invalidation are deterministic enough to code,
3. MTF/session timing is causal,
4. no future information is required,
5. results are produced with real SL/TP resolution and no BE/protected-SL manipulation.
