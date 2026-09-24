# Bermula Native Backtest v1

Updated: 2026-09-24

## Purpose

Test the Paul-X / Bermula technique learned from the supplied 14-video playlist **without applying the user's CASIO constraints**.

This is a source-derived prototype, not a claim that every numeric threshold below was stated verbatim by Paul-X.

## Data

- Instrument: XAUUSD
- Feed: Dukascopy M5
- Period: 2020-01-09 00:00 UTC to 2025-11-26 20:35 UTC
- Bars: 417,740 M5 bars
- No session restriction
- No starting-capital assumption
- No fixed percentage risk
- No fixed R:R
- No break-even or protected-stop logic
- Round-trip friction assumption: 1 bp
- Results expressed in R to avoid imposing arbitrary account sizing

## Technique tested

Only the higher-confidence **Breakout / Continuation** family was tested.

```text
H4 Bermula / SNR origin
    -> H4 structural direction
    -> H1 strong breakout
    -> pullback / role-reversal retest
    -> M5 confirmation
    -> structural SL
    -> S/R-based exit
```

The reversal family is excluded because its exact deterministic trigger is not yet sufficiently resolved from the source material.

## Deterministic operationalization

### H4 Bermula zone

A confirmed H4 swing pivot whose departure reaches at least 1.5 H4 ATR within the next 3 H4 bars.

The full H4 origin candle is used as the zone.

This is an operational definition for testing; the exact Paul-X zone geometry is still unresolved.

### Direction

H4 structural direction:

- higher swing highs + higher swing lows -> bullish,
- lower swing highs + lower swing lows -> bearish.

### Breakout

H1 breakout requires:

- candle body >= 0.8 H1 ATR,
- close beyond the Bermula zone by >= 0.05 H1 ATR,
- direction aligned with H4 structure.

### Pullback

Price may return to the broken zone within 24 hours.

### Lower-timeframe confirmation

M5 confirmation requires a directional break of the previous 5 M5 bars with body >= 0.4 M5 ATR.

This represents the lower-timeframe confirmation / nested micro-structure concept found repeatedly in the lessons. It is a deterministic research mapping, not a verbatim Paul-X formula.

### Stop

Structural stop beyond the opposite side of the H4 Bermula zone plus 0.1 H1 ATR.

### Exit

The videos teach S/R for entry and exit but do not lock one universal target timeframe. Therefore two predeclared structural-exit interpretations were tested with identical entries/stops:

1. nearest causally known H4 opposing S/R swing extreme;
2. nearest causally known H1 opposing S/R swing extreme.

No minimum R:R filter was added after seeing the data.

## Setup funnel

From the full history:

| Stage | Count |
|---|---:|
| H4 displacement-qualified Bermula zones | 257 |
| H1 strong aligned breakout events | 33 |
| Valid pullback/retest | 23 |
| M5 confirmation reached | 14 |
| H4 structural target available | 2 |
| H1 structural target available | 4 |

This funnel is the most important result of v1. The entry sequence is identifiable, but a strict “target must already exist at an opposing historical S/R” interpretation leaves most confirmed continuation setups without an objective target, particularly when gold is breaking into new price territory.

## Result A — H4 S/R exit

| Metric | Result |
|---|---:|
| Trades | 2 |
| Wins | 1 |
| Losses | 1 |
| Win rate | 50.00% |
| Net | -0.577R |
| Expectancy | -0.288R/trade |
| Profit factor | 0.43 |
| Max drawdown | 1.010R |
| Average planned R:R | 1.382 |
| Long / Short | 1 / 1 |

Trades:

| Entry date | Side | Planned R:R | Outcome |
|---|---|---:|---:|
| 2020-04-17 | Short | 2.293R | -1.010R after cost |
| 2025-02-19 | Long | 0.471R | +0.434R after cost |

This sample is too small for a stable performance estimate.

## Result B — H1 S/R exit

| Metric | Result |
|---|---:|
| Trades | 4 |
| Wins | 4 |
| Losses | 0 |
| Win rate | 100.00% |
| Net | +1.932R |
| Expectancy | +0.483R/trade |
| Profit factor | undefined (no losses) |
| Max drawdown | 0.000R |
| Average planned R:R | 0.505 |
| Long / Short | 3 / 1 |

Trades:

| Entry date | Side | Planned R:R | Net result |
|---|---|---:|---:|
| 2020-04-17 | Short | 0.544R | +0.534R |
| 2020-07-27 | Long | 0.490R | +0.462R |
| 2025-02-19 | Long | 0.072R | +0.034R |
| 2025-10-09 | Long | 0.914R | +0.902R |

The 100% win rate is **not evidence of a 100% system**. Four trades are far too few, and the structural H1 targets are generally close: average planned reward is only about 0.51R.

## Interpretation

### What v1 supports

The playlist's core sequence can be detected causally in real XAUUSD data:

```text
Bermula/SNR -> breakout -> pullback -> lower-TF confirmation
```

Out of 33 qualifying breakouts, 23 pulled back and 14 generated the chosen M5 micro-structure confirmation.

### What v1 does not establish

This backtest does not establish the profitability of the full Bermula system.

The decisive missing piece is the creator-native exit/target behavior when price is moving beyond already-known resistance/support. A large share of confirmed continuation entries occur with no prior opposing S/R above/below price. Forcing a target in those cases would require an additional rule such as an extension, measured move, trailing structure, newly formed S/R, or fixed R multiple; none has been sufficiently established from the supplied source set yet.

The reversal setup is also absent from v1 and may materially increase setup count.

### Why no CASIO rules were used

The following were intentionally **not** applied:

- RM100 starting balance,
- 5% risk,
- fixed 1:3,
- New York-only session,
- minimum monthly trade count,
- target win-rate requirement.

Those would test a CASIO adaptation, not the learned Bermula method.

## Research conclusion

Bermula v1 should be treated as a **translation-validation backtest**, not a performance verdict.

The current evidence says:

- the breakout/pullback/confirmation sequence is mechanically identifiable;
- the strict H4-target interpretation is too sparse to evaluate;
- H1 S/R exits are executable more often but produce small structural R:R;
- most confirmed entries still need the missing native exit rule;
- the next highest-value research task is resolving Paul-X's exit weapon and the exact lower-TF confirmation / Miss-Deep-Accurate terminology before evaluating the full method.

## Reproducibility

Code:
- `research/bermula_native_backtest.py`

Workflow:
- `.github/workflows/bermula-native-backtest.yml`

Research branch:
- `research/youtube-playlist-technique`
