# AI Agent Research Plan

The goal is a repeatable research agent that can continue learning this playlist and future trading sources without mixing evidence, interpretation, and backtest results.

## Agent loop

### Stage A — Source acquisition
1. Enumerate playlist videos in order.
2. Capture verified title + URL.
3. Transcribe each video individually.
4. Record inaccessible/deleted/private videos explicitly.

### Stage B — Knowledge extraction
For each video:
1. split by concept/setup,
2. extract atomic trading rules,
3. attach timestamps/evidence,
4. tag DIRECT / DERIVED / HYPOTHESIS,
5. record examples and invalidations,
6. reconcile terminology with prior videos.

### Stage C — Canonical technique model
Build a consolidated rulebook containing:
- market context,
- MTF hierarchy,
- setup families,
- entry logic,
- SL,
- TP,
- invalidation,
- session timing,
- optional vs mandatory filters.

Conflicts are versioned; newer teaching does not automatically overwrite older teaching.

### Stage D — Deterministic translation
Convert discretionary concepts into bounded candidate definitions. Each operationalization must carry:
- source phrase,
- machine definition,
- reason for mapping,
- parameter range,
- confidence.

### Stage E — Backtest implementation
Use causal MTF features and execution resolution from the finest available data.

Current required test contract:
- XAUUSD,
- MTF mandatory,
- New York only, DST-aware,
- RM100 start,
- 5% current-equity risk,
- fixed 1:3 R:R,
- real SL only,
- no BE/protected SL,
- target WR 60%–80%,
- minimum 8 trades/month.

### Stage F — Research ladder
Run in this order:
1. faithful creator baseline,
2. deterministic interpretations for ambiguous rules,
3. individual filter ablations,
4. bounded combinations,
5. yearly/monthly robustness,
6. stress/slippage sensitivity,
7. final untouched holdout.

Do not optimize everything at once.

### Stage G — Promotion
Promote only candidates that have:
- traceable source evidence,
- enough trades,
- robust performance across time,
- no lookahead,
- no accounting tricks,
- reproducible config and report output.

## Suggested agent artifacts

```text
source_manifest.json
video_notes/<video-id>.md
rulebook.yaml
hypotheses.yaml
candidate_configs/
backtest_runs/
reports/
decision_log.md
```

## Research memory principle

Git is the durable memory. Chat conversation is a working interface, not the single source of truth. Important findings, rejected hypotheses, parameter definitions, and reasons for decisions should be committed to this branch.
