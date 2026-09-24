# CASIO A-Grade M5 Sweep/Reclaim + M1 Confirmation — Final Strict Audit

## Current hard monthly rules
1. Minimum 8 trades.
2. Minimum +4R net.
3. Winners > losers.

## Research protocol
- XAUUSD, EURUSD, GBPUSD, GBPJPY.
- Fixed 1R target for this quality-filter study.
- Real structural stop; no BE/protected-stop conversion.
- M5 liquidity sweep/reclaim.
- A-grade pre-entry filters came from winner/loser analysis:
  - overextension against the intended reversal direction;
  - H1 RSI opposing the intended reversal before entry;
  - meaningful M5 reclaim/rejection;
  - structural stop not extremely small vs M5 ATR;
  - M1 micro-BOS confirmation.
- Final portfolio parameters selected using 2017-2022 only.
- 2023-2026 was not used to select the frozen portfolio.

## Frozen portfolio result
- Completed months: 116
- Strict passes (>=8 trades AND >=+4R AND W>L): **104/116**
- Development 2017-2022: **65/72**
- Later validation 2023-2026 through Aug: **39/44**
- Accepted portfolio trades: **9,811**
- Trade-weighted portfolio WR: **51.14%**
- Total monthly net R: **+223R**

## Per-market frozen A-grade quality
| Market | Underlying qualified setups | WR |
|---|---:|---:|
| XAUUSD | 10,468 | 50.24% |
| EURUSD | 12,019 | 51.27% |
| GBPUSD | 13,683 | 51.74% |
| GBPJPY | 7,402 | 50.51% |

## Strict failing months
| Month | Trades | W | L | WR | Net R |
|---|---:|---:|---:|---:|---:|
| 2017-12 | 337 | 150 | 187 | 44.51% | -37R |
| 2018-03 | 35 | 19 | 16 | 54.29% | +3R |
| 2018-08 | 418 | 198 | 220 | 47.37% | -22R |
| 2018-11 | 388 | 182 | 206 | 46.91% | -24R |
| 2021-09 | 15 | 9 | 6 | 60.00% | +3R |
| 2022-03 | 390 | 186 | 204 | 47.69% | -18R |
| 2022-07 | 341 | 158 | 183 | 46.33% | -25R |
| 2023-06 | 387 | 175 | 212 | 45.22% | -37R |
| 2024-11 | 378 | 179 | 199 | 47.35% | -20R |
| 2025-12 | 13 | 8 | 5 | 61.54% | +3R |
| 2026-01 | 391 | 180 | 211 | 46.04% | -31R |
| 2026-03 | 420 | 210 | 210 | 50.00% | 0R |

## Corrected audit note
An intermediate monthly file used an older pass flag and marked +3R months as passes. The final strict audit above explicitly recomputes all three current hard conditions. Therefore the correct result is **104/116**, not 107/116.

## Verdict
**REJECT as a full solution to the current rules.**

Filtering is real and improves quality: the raw sweep family was roughly 48-49% WR on the major FX pairs, while the frozen A-grade portfolio exceeds 51% trade-weighted WR and EURUSD/GBPUSD are the strongest components.

But a small aggregate edge above 50% is not enough to guarantee W>L and +4R every calendar month. Several adverse regimes still produce hundreds of trades with sub-50% realized WR.

Best retained setup concept:

overextended move against intended reversal
-> M5 liquidity sweep + decisive reclaim
-> non-tiny structural stop
-> M1 microstructure break
-> fixed target

Do not cherry-pick validation-period hours or parameters to remove the remaining failed months.
