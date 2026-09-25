# FxPro M1 Reverse-All Research — Progress Report

Date: 2026-09-25

Status: **24 strategy families × 4 markets = 96 original-vs-reverse A/B pairs completed.**

Data: user-supplied **FxPro M1 only** for EURUSD, GBPUSD, GBPJPY and XAUUSD. No Dukascopy data is used in these results.

## Headline

- Reverse expectancy is positive in **20 / 96** pairs.
- Reverse expectancy improves on the original in **38 / 96** pairs.
- Reverse is both positive and better than the original in **13 / 96** pairs.
- Reverse compounds RM100 above RM100 at 5% risk in only **9 / 96** pairs.

Therefore the universal **"all signals are backwards"** hypothesis is rejected. Inversion is concentrated in a small number of strategy/market combinations.

## Strongest exact-code inversion leads

### GBPJPY — V3 Trend M15
- 201 reversed trades
- WR 46.77%
- expectancy **+0.178R/trade**
- PF **1.35**
- RM100 -> **RM376.72**
- max compounded DD **40.94%**
- original expectancy: **-0.158R/trade**
- delta: **+0.336R/trade**
- about 2.1 trades/month
- 2026 YTD is slightly negative

This is currently the cleanest exact-code inversion result.

### GBPJPY — V5 Native M15
- 288 reversed trades
- WR 42.01%
- expectancy **+0.122R/trade**
- PF **1.22**
- RM100 -> **RM283.49**
- max compounded DD **50.82%**
- original expectancy: **-0.098R/trade**
- delta: **+0.221R/trade**
- about 2.7 trades/month
- 2026 YTD is negative

This independently supports a GBPJPY trend/structure exhaustion hypothesis, but frequency is low.

## Other notable lead

Reversed ADX/DI M15 at 3R improves sharply on GBPUSD and GBPJPY:

- GBPUSD: 878 trades, 27.68% WR, +0.107R/trade, PF 1.15, RM100 -> RM401.85, DD 86.70%
- GBPJPY: 785 trades, 27.26% WR, +0.090R/trade, PF 1.12, RM100 -> RM186.00, DD 86.27%

Important: this ADX/DI implementation is a reconstruction from the preserved documented rules, not recovered original executable source. The edge is interesting but the 5%-risk path is still unacceptable.

## BBMA finding

The old BBMA Cleaner Core can look strong reversed under its legacy management, but that management contains the previously rejected protected-stop behavior.

Under the standardized **real-SL, fixed-3R** BBMA test:

- GBPUSD reverse: +0.033R/trade but ~98.4% DD
- GBPJPY reverse: +0.036R/trade but ~99.6% DD
- EURUSD reverse: negative
- XAUUSD reverse: negative

So the screenshot hypothesis does **not** generalize into a deployable "reverse BBMA everywhere" system.

## FiboRSI8 finding

Both recovered FiboRSI8 variants become worse when reversed on **all four markets**. This is strong evidence against inversion for that family.

## Working interpretation

The useful hypothesis is no longer "reverse everything."

The data instead suggests that **some trend/structure signals are functioning as exhaustion-event detectors on specific markets**, most clearly GBPJPY. The next legitimate test is whether a simple, causal orientation condition can distinguish when the same setup should be followed versus faded—without tuning by year.

Older strategy transfers whose exact executable source was not preserved (including some Bermula/ICT/S&D implementations) are not being falsely labelled as exact-code retests. They require explicit reconstruction before being added to the master table.
