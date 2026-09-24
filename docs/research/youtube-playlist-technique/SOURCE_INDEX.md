# Source Index

## Playlist

- URL: https://youtube.com/playlist?list=PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O
- ID: `PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O`
- Status: authoritative playlist supplied by the user; 14 individual video URLs received and normalized.

## Ingestion notes

The normal web fetch for YouTube is throttled in this environment. A playlist-level transcription attempt failed because a playlist URL is not a single video input, but individual YouTube video URLs are accepted by the installed transcription pipeline.

Video-level ingestion therefore proceeds sequentially. Research claims must not be inferred from URL metadata alone.

## Video inventory

| # | Video ID | Canonical URL | Transcript | Rule extraction | Notes |
|---:|---|---|---|---|---|
| 1 | YrhZ6GgnK5c | https://www.youtube.com/watch?v=YrhZ6GgnK5c | submitted | pending | user link started at 87s; full canonical video is used |
| 2 | P8vqReoSrc0 | https://www.youtube.com/watch?v=P8vqReoSrc0 | pending | pending | |
| 3 | cAdsNw4fF1A | https://www.youtube.com/watch?v=cAdsNw4fF1A | pending | pending | |
| 4 | tJyGCF8bO4I | https://www.youtube.com/watch?v=tJyGCF8bO4I | pending | pending | |
| 5 | s3UhrC0mH_4 | https://www.youtube.com/watch?v=s3UhrC0mH_4 | pending | pending | |
| 6 | hCGPJhXZ_vI | https://www.youtube.com/watch?v=hCGPJhXZ_vI | pending | pending | |
| 7 | zBOAkngvwhE | https://www.youtube.com/watch?v=zBOAkngvwhE | pending | pending | |
| 8 | HQsLnfpxDBc | https://www.youtube.com/watch?v=HQsLnfpxDBc | pending | pending | |
| 9 | UhX56Q06b2w | https://www.youtube.com/watch?v=UhX56Q06b2w | pending | pending | |
| 10 | VdycDzD0n7A | https://www.youtube.com/watch?v=VdycDzD0n7A | pending | pending | |
| 11 | 3KLZNfctUsA | https://www.youtube.com/watch?v=3KLZNfctUsA | pending | pending | |
| 12 | XdPyQE4QUjw | https://www.youtube.com/watch?v=XdPyQE4QUjw | pending | pending | |
| 13 | TTEmmvHfKZE | https://www.youtube.com/watch?v=TTEmmvHfKZE | pending | pending | |
| 14 | Sm1Gh_49T7s | https://www.youtube.com/watch?v=Sm1Gh_49T7s | pending | pending | |

## Per-video evidence package

For every video, store:

- title and URL,
- transcript/caption-derived rule notes,
- timestamps for rule-bearing statements,
- screenshots/visual observations only when materially needed,
- atomic rules,
- examples and counterexamples,
- ambiguities,
- contradictions with earlier/later lessons,
- proposed deterministic operationalization,
- confidence tag: DIRECT / DERIVED / HYPOTHESIS / TESTED.

## Copyright handling

Store concise research notes and rule abstractions, not wholesale copyrighted transcript reproduction. Raw transcript text should only be retained when needed for analysis and should not be unnecessarily duplicated in Git.
