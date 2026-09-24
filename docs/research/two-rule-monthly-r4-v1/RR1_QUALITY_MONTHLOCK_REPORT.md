# RR1 Quality-Filtered Four-Market Month-Lock Audit

Date: 2026-09-25

## Monthly hard gates

1. At least 8 completed trades.
2. At least +4R realized net result.
3. Winners > losers.

Because the tested version uses fixed +1R / -1R exits, conditions 2 and 3 are aligned: +4R necessarily implies more wins than losses.

## Method

- Instruments: XAUUSD, EURUSD, GBPUSD, GBPJPY.
- Base family: M5 liquidity sweep -> reclaim -> structural stop.
- Fixed 1R target.
- Quality features use pre-entry information only.
- Quality filters were developed before later-period validation.
- One position per instrument at a time.
- Cross-instrument positions may overlap.
- Monthly router stops opening new trades only after at least 8 trades have been realized and realized monthly R >= +4R.
- Trades already open when the lock condition is reached are allowed to finish; their outcomes remain part of the month.
- Same-bar stop/target ambiguity is resolved stop-first.

## Search

Top 8 development-selected quality variants were retained for each market.
All 8 x 8 x 8 x 8 = 4,096 four-market portfolios were tested with the causal month-lock.

### Best result

No portfolio passed all 116 completed months.

Best total coverage:
- 107 / 116 completed months pass.
- Best later-validation coverage among top portfolios: 42 / 44.
- Development-prioritized frozen selection: 66 / 72 development months and 41 / 44 later-validation months, total 107 / 116.

## Development-prioritized frozen selection

| Symbol | Lookback | Min wick frac | Min reclaim close | M1 body min | Min stop ATR | H1 opposition | Min distance ATR | Full-sample WR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 20 | 0.40 | 0.50 | 0.30 | 0.50 | 5.0 | 0.0 | 50.24% |
| EURUSD | 10 | 0.20 | 0.50 | 0.50 | 0.70 | 5.0 | 0.5 | 51.27% |
| GBPUSD | 10 | 0.20 | 0.50 | 0.30 | 0.50 | 5.0 | 0.5 | 51.74% |
| GBPJPY | 10 | 0.40 | 0.50 | 0.50 | 0.70 | 10.0 | 0.5 | 50.51% |

## Failed completed months for the development-prioritized selection

| Month | Trades | Wins | Losses | Net R |
|---|---:|---:|---:|---:|
| 2017-12 | 337 | 150 | 187 | -37R |
| 2018-08 | 418 | 198 | 220 | -22R |
| 2018-11 | 388 | 182 | 206 | -24R |
| 2022-03 | 390 | 186 | 204 | -18R |
| 2022-07 | 341 | 158 | 183 | -25R |
| 2023-06 | 387 | 175 | 212 | -37R |
| 2024-11 | 378 | 179 | 199 | -20R |
| 2026-01 | 391 | 180 | 211 | -31R |
| 2026-03 | 420 | 210 | 210 | 0R |

## 2026 status

- Jan: FAIL, -31R, 180W / 211L.
- Feb: PASS, +4R, 24W / 20L.
- Mar: FAIL, 0R, 210W / 210L.
- Apr: PASS, +5R, 17W / 12L.
- May: PASS, +4R, 48W / 44L.
- Jun: PASS, +4R, 176W / 172L.
- Jul: PASS, +4R, 70W / 66L.
- Aug: PASS, +4R, 12W / 8L.

## Verdict

The 1R quality-filtered liquidity-sweep family materially improves W/L balance, but it does not satisfy the user's three monthly hard gates in every completed month. No 4-market combination from the 4,096 frozen portfolio search achieved 116/116.

Do not promote this version as compliant.