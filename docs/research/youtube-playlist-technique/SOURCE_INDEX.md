# Source Index

## Playlist

- URL: https://youtube.com/playlist?list=PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O
- ID: `PLaXZkBcBhVzi7KYG3bcbHCJGqEzdW044O`
- Status: playlist accepted as the authoritative source supplied by the user.

## Ingestion notes

The normal web fetch for the YouTube playlist was throttled. A playlist-level transcription submission was also attempted with a YouTube-capable transcriber, but playlist URLs are not accepted as a single transcribable video. The failed job refunded its credits.

Therefore, the next reliable ingestion path is to enumerate the playlist into individual video URLs and transcribe/analyze each video independently.

## Video inventory

Populate this table only from verified playlist entries.

| # | Video title | Video URL | Transcript | Rule extraction | Notes |
|---:|---|---|---|---|---|
| 1 | pending enumeration | pending | pending | pending | Do not infer content before source access |

## Per-video evidence package

For every video, store:

- title and URL,
- transcript or caption text where available,
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
