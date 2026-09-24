# Research Status

Updated: 2026-09-24

## Completed

- Created isolated branch: `research/youtube-playlist-technique`.
- Registered all 14 supplied YouTube videos in `source_manifest.json`.
- Built GitHub Actions caption-ingestion workflow and reusable research script.
- Successfully extracted caption evidence for all 14 videos; Video 03's automatic language transcription remains unusable for detailed rule extraction.
- Performed expanded Malay/Indonesian keyword evidence pass.
- Created `VIDEO_NOTES_PHASE1.md` covering all 14 lessons.
- Created `RULEBOOK_V0.md` with source-timestamped DIRECT rules, DERIVED rules, conflicts and unresolved terminology.
- Created machine-readable `rulebook.yaml` for future agent/research automation.
- Cross-checked the wider Paul-X course ecosystem; related indexing confirms SNR/FTR, valid SNR, reversal/continuation, Miss/Deep/Accurate, entry and multi-timeframe lessons.

## Strongest rules learned so far

1. S/R is the base map.
2. Bermula = origin area of meaningful rise/fall.
3. Strong displacement/breakout matters.
4. Breakout -> pullback -> entry is an explicit SOP.
5. Entry requires confirmation.
6. Confirmation is sought on a lower timeframe.
7. Broken resistance/support can flip role.
8. Fresh/untouched zones are preferred.
9. Higher timeframe supplies context; lower timeframe supplies execution.
10. Reversal and continuation are distinct setup families.

## Current unresolved items

- Exact zone boundaries (body/wick/base/full origin candle).
- Exact deterministic lower-timeframe confirmation trigger.
- Context behind the breakout-before-close statement vs close-back-inside invalidation.
- Proprietary/ASR terms: SMA, FM, facelift, Miss, Deep, Accurate.
- Creator-native TP/exit hierarchy.
- Video 03 needs alternative source/caption recovery for useful text.

## Current research state

**Not yet ready for a faithful backtest.**

A prototype continuation engine could already be built, but doing so now would require hypotheses for zone geometry and confirmation. Those hypotheses are documented separately and must not be represented as Paul-X's original rules.

## Next research actions

1. Resolve confirmation taxonomy, especially Miss / Deep / Accurate and nested lower-TF Bermula behavior.
2. Resolve zone drawing boundaries from examples or alternate copies.
3. Lock a faithful continuation/breakout specification.
4. Lock a faithful reversal specification.
5. Only then implement causal MTF backtest under the current CASIO contract.
