# CASIO Native FX Scalping Research — 2R

## Frozen user rules
- RR fixed 1:2
- 5% current-equity risk per entry
- minimum 8 trades per month
- every month must be positive
- real SL only
- no BE / protected SL
- scalping: small pip movement
- EURUSD + GBPUSD + GBPJPY
- FxPro M1, 2017 through 2026 YTD

## Native scalp setup
1. Sweep/reclaim of recent M1 liquidity.
2. M1 micro break of the sweep candle within a few minutes.
3. Entry on the next M1 open.
4. Structural stop beyond the sweep-to-confirmation wick.
5. Fixed 2R target.

Development-selected pair versions:
- EURUSD: prior 20-M1 liquidity, stop <=2 pips, rejection wick >=20%, confirm <=2 minutes.
- GBPUSD: prior 30-M1 liquidity, stop <=2 pips, rejection wick >=40%, confirm <=3 minutes.
- GBPJPY: prior 30-M1 liquidity, stop <=3 pips, rejection wick >=60%, confirm <=2 minutes.

Selection window: 2017-2022 only.
Validation: 2023-2026 YTD.

A previously frozen 2R CASIO rescue sleeve is allowed from calendar day 10 onward if the month has not yet met the objective. No open trade is modified. The portfolio stops taking new entries for the month once the objective is met.

## Raw native scalp quality
- 58,565 historical trades before monthly stopping.
- WR: 35.76%.
- Gross PF at 2R: 1.113.

## Positive-R monthly policy
If the objective is literal positive additive R:
- 116/116 completed months positive through August 2026.
- 72/72 development months positive.
- 44/44 validation months positive.
- minimum 8 trades/month.
- average accepted trades/month about 22.35.
- 2,601 accepted trades.
- WR 36.52%.
- PF 1.151.
- +249R.

## Positive R is not necessarily positive money
At 5% current-equity sizing, sequence/geometric drag matters.

Under the stronger rule:
- reset to RM100 each month;
- require at least 8 trades;
- stop only when the compounded balance is above RM100;

the result is:
- 114/116 completed months finish above RM100.
- 71/72 development months positive in money.
- 43/44 validation months positive in money.

Failures:
- 2019-04: 560 trades, -17R, RM100 -> RM11.20.
- 2024-04: 618 trades, +15R additive, but RM100 -> RM46.49 because of severe sequence/geometric drag.

## 2026 monthly-reset result under the positive-money rule
| Month | Trades | Net R | RM100 -> |
|---|---:|---:|---:|
| Jan | 30 | +3R | RM107.66 |
| Feb | 8 | +4R | RM119.25 |
| Mar | 187 | +11R | RM108.76 |
| Apr | 8 | +1R | RM102.99 |
| May | 8 | +10R | RM159.88 |
| Jun | 8 | +7R | RM138.08 |
| Jul | 11 | +1R | RM102.24 |
| Aug | 8 | +7R | RM138.08 |
| Sep YTD | 8 | +1R | RM102.99 |

## Verdict
REJECT as the final scalping system.

The native scalp setup solves frequency and can force positive additive-R months with a causal stopping policy, but the raw edge is too thin and the practical money objective still fails in 2 historical months. Some months also require hundreds of trades, making spread/commission a serious concern.

The next research target should be a higher-quality native scalp edge, not a stronger rescue mechanism.
