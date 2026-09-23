# CASIO New York-Only Strict Search — 2017–2020

Branch: `research/historical-2017-2020`

## Hard target

Every strategy is pass/fail against:

- Starting equity RM100.
- 5% current-equity risk per entry.
- Fixed target 3R.
- Win rate >= 60%.
- Maximum drawdown <= 25%.
- Minimum 8 realized trades in every calendar month.
- Profitable in each calendar year 2017, 2018, 2019 and 2020.
- New York session only.
- Real structural stop only: no breakeven/protected-stop manipulation.
- Conservative intrabar convention: if SL and TP are both touched on the same execution bar, SL wins.
- 1 bp round-trip cost.
- 2021+ remains sealed during development.

## Important session correction

Earlier generic session research often used fixed UTC windows. This NY-specific research uses `America/New_York` local time and therefore follows daylight-saving-time changes in 2017–2020.

Tested NY windows include:
- NY Full: 08:00–17:00 ET.
- NY Core: 08:30–12:30 ET.
- NY Cash AM: 09:30–12:30 ET.
- Open window: 08:30–10:30 ET.
- AM Silver-Bullet-style window: 10:00–11:00 ET.
- PM Silver-Bullet-style window: 14:00–15:00 ET.

Most new NY engines also cap execution at one entry per New York trading date. This is a cadence rule, not stop manipulation.

## Completed NY-only searches

### Broad DST-aware NY strict grid

Workflow run: 35860462612

- 4,446 configurations.
- Families: EMA20/EMA50 pullback, NY VWAP trend reclaim, VWAP fade, rolling liquidity sweep, overnight sweep, premarket sweep, previous-NY sweep, opening-range breakout, initial-balance breakout, overnight breakout, RSI2 trend pullback, FVG trend, displacement.
- Entry modes: market, half retrace, 70.5% retrace, 88.6% retrace, FVG midpoint where relevant.
- HTF bias: H4, H4+D1, H1+H4+D1.
- Strict passes: **0**.

Closest overall development candidate:

`NY__displacement__h4__NY_CASH_AM__deep705__A28__V1.15__L48`

- 69 trades.
- 44.93% WR.
- +0.565R/trade.
- PF 1.83.
- 25.18% max DD.
- 1.44 trades/month average.
- minimum month 0.
- 4/4 profitable years.

Yearly:
| Year | Trades | WR | ExpR | PF | DD | RM100 -> |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 15 | 53.33% | +0.886 | 2.53 | 23.61% | RM178.91 |
| 2018 | 18 | 38.89% | +0.305 | 1.39 | 22.97% | RM120.91 |
| 2019 | 17 | 41.18% | +0.381 | 1.51 | 17.56% | RM127.49 |
| 2020 | 19 | 47.37% | +0.720 | 2.16 | 16.98% | RM179.22 |

This nearly meets the DD target and has strong expectancy/PF in all four years, but fails WR and frequency badly.

A stricter H4+D1 version:

`NY__displacement__h4d1__NY_CASH_AM__deep705__A28__V1.15__L48`

- 48 trades.
- 43.75% WR.
- +0.517R.
- PF 1.74.
- 25.33% DD.
- 1.00 trade/month average.
- min month 0.
- 4/4 profitable years.

2017 alone reached 60% WR with PF 3.34 and DD12.84%, but that precision did not persist in 2018–2020.

### Focused NY shortlist

Workflow run: 35860874011

- 840 configurations.
- Families: impulse breakout, EMA20, VWAP, overnight sweep, opening-range retest, overnight retest, RSI2.
- Strict passes: **0**.

Best robust result:
`NYFAST__RSI2__h4d1__NY_CORE__market0__A18__V0.8`
- 101 trades.
- 31.68% WR.
- +0.124R.
- PF 1.16.
- 38.15% DD.
- 2.10 trades/month.
- min month 0.
- 4/4 profitable years.

### NY confluence scoring

Workflow run: 35860720848

- 1,944 configurations.
- Causal score uses EMA stack, NY VWAP relation, DI, ADX, volume, opening-range location and completed H1 trend.
- Triggers: EMA20 touch, VWAP touch, RSI2 reclaim, OR retest, overnight retest, breakout.
- Strict passes: **0**.

Best all-four-year confluence examples:
- OR retest H4+D1, score6, ADX20, volume1.2, deep70.5:
  - 39 trades, 38.46% WR, +0.107R, PF1.12, DD33.13%, 0.81/month, min0, 4/4 years.
- RSI2 reclaim H4+D1, score5, ADX20, volume0.8, market:
  - 177 trades, 32.20% WR, +0.107R, PF1.13, DD50.22%, 3.69/month, min0, 4/4 years.
- RSI2 reclaim H4, score5, ADX14, volume0.8:
  - 323 trades, 30.96% WR, +0.055R, PF1.07, DD64.57%, 6.73/month, min3, 4/4 years.

Confluence did not raise WR toward 60% while preserving frequency.

### NY sweep -> MSS -> FVG -> midpoint retrace

Workflow run: 35861516677

- 2,304 configurations.
- Liquidity sources: rolling highs/lows, overnight high/low, previous NY high/low, opening-range high/low.
- Windows: NY open, 10–11 AM ET, 2–3 PM ET, NY core.
- Confirmation: causal market-structure shift plus displacement, later FVG, pending entry at FVG midpoint.
- Real SL beyond sweep extreme.
- Strict passes: **0**.

The only >=60% WR variants were tiny samples:
- 5 trades total at 60% WR, +1.351R, PF4.22, DD5.28%, min month0, only 3/4 years.
- 3 trades total at 66.67% WR, +1.611R, PF5.58, DD5.27%, min month0, only 2/4 years.

Increasing occurrence count drops WR well below 60%.

## Completed NY-only search count

- Broad NY grid: 4,446
- Focused NY shortlist: 840
- NY confluence grid: 1,944
- NY sweep/MSS/FVG grid: 2,304

**Total completed NY-only configurations: 9,534**

No configuration meets all hard requirements.

## Empirical frontier

The strongest balance found so far is the NY Cash-AM displacement/deep-70.5% retracement family:
- around 43–45% WR,
- +0.5R/trade expectancy,
- PF around 1.7–1.8,
- 4/4 profitable development years,
- DD approximately 25–31% when highly selective,
- but only ~1–1.5 trades/month.

When frequency is increased toward the required level, WR generally falls toward 30–35% and drawdown rises materially.

When precision is tightened enough to reach observed 60%+ WR, sample size collapses to a handful of trades over four years.

## Decision

No NY-only strategy is promoted.

The hard target remains unchanged.

A DST-aware Dukascopy M1 precision engine has also been added to test whether M15 NY setups can be improved through deep retracement + M1 confirmation while preserving fixed 3R and real stops. Its results are intentionally not included here until its full 2017–2020 run completes.

2021–2026 remains sealed.
