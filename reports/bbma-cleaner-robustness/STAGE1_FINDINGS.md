# BBMA Cleaner Core — Robustness Stage 1

Date: 2026-09-20

## Frozen research configuration

This branch freezes the cleaner BBMA core so the same implementation can be replayed across feeds.

- Entry families: `RRR_CSM`, `CSM_CSM_RE`, `H1_RE_M15_CSM_M5_RE`
- H4 major-trend veto
- H1/M15 previous-closed causal context
- strict state freshness: H1 <= 1 bar, M15 <= 1 bar
- M5 structural stop, 0.15 ATR buffer
- accepted stop distance: 0.8-1.8 M5 ATR
- +0.5R protection -> +0.25R stop
- 50% at 3R, 50% runner to 4R
- opposite CSM/CSAK exit
- max 2 entries/day, 60 M5-bar cooldown
- RM100 reset each calendar year, 5% current-equity risk per trade

## Reproducibility correction

The earlier conversational cleaner-core summary was not backed by an exact committed replay. Reconstructing and freezing the stated rules did **not** reproduce the earlier 10/10-positive-year claim. The reproducible gross FxPro candidate is still positive, but materially weaker and more regime-dependent.

## FxPro 2017-2026 gross result

Chosen frozen candidate:

- 1,353 trades
- 11.56 trades/month
- +0.0619R/trade
- PF 1.19
- 9/10 calendar years above RM100
- worst yearly ending balance RM84.53
- worst yearly max drawdown 51.53%
- 63/117 months positive
- 13/106 rolling 12-month windows negative

Family stability is weak: the dominant family contribution flips between 2024 and 2025.

## Parameter-neighborhood checks

Nearby 3R/4R exit settings remained gross-positive, so the edge is not caused by one exact TP value. However calendar-year stability remained weak.

Reducing the minimum accepted structural stop from 1.0 ATR to 0.8 ATR improved gross calendar consistency, but also increased sensitivity to spread because transaction cost becomes a larger fraction of 1R.

## Independent feed validation, common 2024-2025 window

| Feed | Trades | Trades/mo | Avg R | PF | 2024 end RM | 2025 end RM |
|---|---:|---:|---:|---:|---:|---:|
| FxPro | 284 | 11.83 | +0.0578R | 1.16 | 115.23 | 128.75 |
| Dukascopy | 288 | 12.00 | +0.0307R | 1.08 | 87.57 | 119.31 |
| OctaFX | 270 | 11.25 | +0.0436R | 1.12 | 77.00 | 158.61 |

The gross edge therefore appears on all three feeds in aggregate, but 2024 is not robust: Dukascopy and OctaFX both finish the year below RM100.

## Execution timing stress

Entering on the next M5 open rather than the signal close does not destroy the gross edge.

2024-2025:

- Dukascopy: 317 trades, +0.0613R/trade, PF 1.18
- OctaFX: 302 trades, +0.0628R/trade, PF 1.19

Therefore signal-close fill optimism is not the main weakness.

## Friction stress

FxPro full-history gross edge: +0.0619R/trade.

Because the median structural risk distance is small, the calculated break-even all-in price friction is only about **$0.093/oz per round trip**.

FxPro full-history sensitivity:

| All-in price cost | Avg R/trade | PF |
|---:|---:|---:|
| $0.02 | +0.0486R | 1.15 |
| $0.05 | +0.0286R | 1.09 |
| $0.075 | +0.0120R | 1.04 |
| $0.10 | -0.0046R | 0.99 |
| $0.15 | -0.0379R | 0.90 |
| $0.20 | -0.0711R | 0.81 |

Independent-feed 2024-2025 cost stress:

### Dukascopy
- $0.05: +0.0121R/trade, PF 1.03
- $0.10: -0.0064R/trade, PF 0.98

### OctaFX
- $0.05: +0.0255R/trade, PF 1.07
- $0.10: +0.0074R/trade, PF 1.02

At $0.10, 2024 remains materially negative on both independent feeds.

## Attempted robustness repairs

### Minimum absolute stop distance
Charging $0.17/oz and filtering out trades with small structural stops improves drawdown, but destroys frequency.

Examples:
- >= $3 stop: ~5.1 trades/month, ~flat expectancy
- >= $4 stop: ~3.5 trades/month, +0.0266R/trade, PF 1.08
- >= $5 stop: ~2.5 trades/month, +0.0521R/trade, PF 1.16

This cannot satisfy the >=8/month objective.

### Stable weak-hour veto
Removing entry hours that were negative in both 2017-2021 and 2022-2026 retained ~9 trades/month but remained slightly negative after $0.17 friction (PF ~0.99).

### Wider M15-style structural swing
Using 12-36 M5 bars for a wider stop lowered frequency and generally worsened expectancy after friction. The farther 3R/4R targets offset the lower transaction-cost drag.

## Stage-1 verdict

**Do not promote this cleaner core as-is.**

The gross BBMA entry edge is real enough to reproduce across three feeds, and 3R/4R management is not the issue. The failure is the combination of:

1. small M5 structural risk distances,
2. transaction-cost drag,
3. a recurring weak regime (especially 2024 on independent feeds), and
4. 5% compounding risk amplifying those weak regimes.

The next research stage should change the *quality of accepted entries*, not merely tweak TP/SL:
- seek a causal BBMA regime gate that removes 2024-type conditions,
- require stronger MTF continuation evidence before M5 execution,
- test session-specific spread/edge interaction using actual bid/ask or tick spread data where available,
- preserve 3R/4R asymmetric exits and 5% risk while targeting >=8 trades/month.

No production/main strategy was changed in this stage.
