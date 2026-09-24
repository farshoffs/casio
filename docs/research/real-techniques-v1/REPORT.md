# CASIO Real-Technique Comparison v1 — FxPro M1 2017–2026 YTD

Date: 2026-09-24

## Frozen common engine

- User-supplied FxPro XAUUSD M1, 2017-01-02 through 2026-09-24
- causal MTF context
- M1 entry and SL/TP chronology
- fixed 3R
- real structural SL only
- no BE / protected SL / partial-profit conversion
- one position at a time
- same-M1 SL+TP collision = SL first
- 1 bp round-trip price-cost stress converted to R from actual structural risk
- RM100 continuous account, 5% current-equity risk

Acceptance:
- >=8 trades in every completed month
- PF >=1.30 after cost
- 10/10 positive year rows

## 1. BBMA OA Canonical MTF Reentry

Source concepts:
- D1/H4 trend from EMA50 + Mid BB
- Reentry after CSAK/CSM
- MA5/MA10 reentry area
- RRE / REE / REM three-TF validation
- lower TF must form same-direction setup

Mechanical test:
D1+H4 direction -> M15 Reentry -> M5/M1 RRE/REE/REM validation -> M15 structural SL -> fixed 3R.

Literal exact lower-TF state:
- 7 trades
- 14.29% WR
- -3.75R after 1bp
- PF 0.44

Practical synchronized interpretation (recent lower-TF R/E/M while M15 is in Reentry):
- 210 trades
- 28.10% WR
- +26R gross
- +5.31R after 1bp
- PF 1.032
- 1.81 trades/month
- 0/116 completed months >=8
- 4/10 positive years
- RM100 -> RM58.64 at 5% after cost
- 83.86% max DD

## 2. Pure Supply & Demand First-Retest MTF

Mechanical test:
H4 price structure -> M15 compact base + strong departure -> fresh first retest only -> M5 directional structure break -> distal-zone structural SL -> fixed 3R.

Result:
- 3,407 trades
- 26.36% WR
- +185R gross
- -78.58R after 1bp
- PF 0.971
- 29.19 trades/month
- minimum completed month = 15
- 116/116 completed months >=8
- 3/10 positive years
- continuous RM100 at 5% after cost effectively collapses
- ~100% max DD

## 3. Naked S/R Reversal + Breakout/Retest

Mechanical test:
H4 price structure -> confirmed H1 swing levels -> M15 rejection/sweep OR decisive break + first retest -> M5 microstructure confirmation -> structural SL -> fixed 3R.

Combined result:
- 2,896 trades
- 26.00% WR
- +116R gross
- -43.34R after 1bp
- PF 0.981
- 24.78 trades/month
- minimum completed month = 4
- 115/116 completed months >=8
- 6/10 positive years
- continuous RM100 at 5% after cost effectively collapses
- ~100% max DD

Sleeve diagnostic:
- reversal: 1,811 trades, 26.56% WR, +113R gross, +6.46R after 1bp, PF ~1.005
- breakout/retest: 1,085 trades, 25.07% WR, +3R gross, -49.80R after 1bp, PF ~0.942

The breakout/retest sleeve is the main drag. Reversal is near breakeven after cost but far below the PF 1.30 gate.

## Acceptance matrix

| Strategy | >=8 every completed month | PF >=1.30 after cost | 10/10 positive years | Verdict |
|---|---|---|---|---|
| BBMA OA MTF Reentry | FAIL | FAIL | FAIL | REJECT v1 |
| Pure S&D First Retest | PASS | FAIL | FAIL | REJECT v1 |
| Naked S/R Reversal + Break/Retest | FAIL (115/116) | FAIL | FAIL | REJECT v1 |

## Research verdict

No production candidate.

Key findings:
1. Canonical BBMA MTF confirmation is too selective and its practical synchronized version still has only ~1.8 trades/month with PF ~1.03 after cost.
2. Pure S&D solves frequency cleanly, but the first-retest edge is too close to 25% WR at 3R and is erased by friction.
3. Naked S/R almost solves frequency, but break/retest is negative after cost and the reversal sleeve is only around breakeven.
4. None approaches PF >=1.30 after cost + 10/10 positive years.

Do not grid-search arbitrary thresholds on this result. Any next stage should change setup quality in practitioner-recognizable ways (zone quality/context, level quality, failed-auction structure) rather than optimize numbers until a pass appears.
