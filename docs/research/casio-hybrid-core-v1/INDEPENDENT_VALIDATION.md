# CASIO Hybrid Core v1 — Independent Feed Validation

Date: 2026-09-24

## Frozen rule

No parameters were changed from the FxPro research result.

Architecture:
- H4 regime / directional context
- H1 double-opposition veto
- M15 event modules: V1 Momentum + Structural Frequency
- explicit false->true setup events with 2-M15-bar cooldown
- strong-trend router prioritizes V1; mixed router prioritizes Structural Frequency and requires SF support for V1
- 180-calendar-day shadow-health gate
- minimum 20 already-closed shadow setups per module
- module enabled only while trailing closed-shadow net R is positive
- fixed 3R
- real structural stop
- no BE / protected stop
- one portfolio position at a time
- 1 bp round-trip cost sensitivity

Independent feeds are M5, so stop/target chronology is resolved on M5. FxPro was therefore also rerun through the same M5-resolution adapter.

FxPro M5 parity checksum:
- 1,296 trades
- +149.51R after 1bp
- PF 1.156
- RM100 @1% -> RM361.11
- max DD 23.44%

Original FxPro M1:
- +157.56R
- PF 1.165
- RM100 @1% -> RM391.10
- max DD 22.98%

M5-vs-M1 execution is therefore not the main reason for the independent-feed result.

## Feed coverage

- FxPro: user M1, 2017-01-02 through 2026-09-24.
- Dukascopy research M5: available from 2025-06-23 through 2026-09-16 in the current research copy.
- OctaFX / Octa Markets MT4 M5: long secondary history; long comparison uses 2017-01-01 through 2025-12-31.

## Long-history comparison — 2017-2025

| Feed | Trades | WR | Net R @1bp | Exp/trade | PF | RM100 @1% | Max DD @1% |
|---|---:|---:|---:|---:|---:|---:|---:|
| FxPro M5 parity | 1,118 | 28.53% | +107.59R | +0.096R | 1.129 | RM244.87 | 23.44% |
| OctaFX M5 | 1,736 | 25.75% | -25.78R | -0.0148R | 0.981 | RM59.46 | 54.00% |

OctaFX fails the production robustness gate.

OctaFX 2017-2025 yearly:
- 2017: -9.00R, PF 0.934
- 2018: -23.73R, PF 0.885
- 2019: +3.57R, PF 1.033
- 2020: +22.64R, PF 1.109
- 2021: -21.94R, PF 0.821
- 2022: -11.19R, PF 0.921
- 2023: +11.78R, PF 1.142
- 2024: -17.10R, PF 0.894
- 2025: +19.18R, PF 1.107

Only 4 of 9 complete OctaFX years are positive after 1bp.

## Recent overlap — 2025-06-23 to 2026-09-16

| Feed | Trades | WR | Net R @1bp | Exp/trade | PF | RM100 @1% | Max DD @1% |
|---|---:|---:|---:|---:|---:|---:|---:|
| FxPro M5 parity | 250 | 32.80% | +71.74R | +0.287R | 1.416 | RM195.99 | 9.72% |
| Dukascopy M5 | 366 | 30.33% | +68.90R | +0.188R | 1.264 | RM187.25 | 19.59% |

Dukascopy confirms that the recent 2025-2026 edge appears on a second feed. It does not rescue the long-history rejection from OctaFX.

## Cost sensitivity

Dukascopy recent sample:
- 0bp: +78.00R, PF 1.306
- 0.5bp: +73.45R, PF 1.284
- 1bp: +68.90R, PF 1.264
- 1.5bp: +64.34R, PF 1.243
- 2bp: +59.79R, PF 1.223

OctaFX 2017-2025:
- 0bp: +52.00R, PF 1.040
- 0.5bp: +13.11R, PF 1.010
- 1bp: -25.78R, PF 0.981
- 1.5bp: -64.67R, PF 0.953
- 2bp: -103.56R, PF 0.926

The OctaFX edge is too thin even before costs and disappears around 0.5-1bp.

## Signal parity

Within the same overlap periods:
- ~64% of FxPro routed trades have a same-direction Dukascopy routed trade within +/-15 minutes.
- ~59% of FxPro routed trades have a same-direction OctaFX routed trade within +/-15 minutes.

The strategy is materially feed-dependent at the individual-signal level.

## Verdict

**CASIO Hybrid Core v1 FAILS independent-feed production validation.**

What survived:
- recent 2025-2026 regime is positive on both FxPro and Dukascopy;
- shadow-health architecture improves path behavior;
- M5 vs M1 execution resolution is not the main source of failure.

What failed:
- long-history edge does not survive OctaFX after realistic cost sensitivity;
- OctaFX 2017-2025 expectancy is negative at 1bp and PF < 1;
- only 4/9 complete OctaFX years are positive;
- cross-feed signal parity is only moderate.

Research decision:
- do not deploy Hybrid Core v1;
- do not retune it on OctaFX after seeing this result;
- archive as a rejected production candidate / useful research architecture;
- require multi-feed agreement during development for the next candidate.
