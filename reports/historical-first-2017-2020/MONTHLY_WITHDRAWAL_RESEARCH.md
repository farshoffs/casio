# CASIO — New York Monthly Withdrawal Research (2017–2020)

## Objective reset

The original minimum-8-trades-per-month rule was only a proxy for the real objective.

The real development objective is now:

- XAUUSD.
- New York session only, DST-aware using `America/New_York`.
- Start RM100.
- Risk 5% of current trading equity per entry.
- Fixed TP = 3R.
- Real structural SL only; no breakeven/protected-SL manipulation.
- Maximum DD target <=25%.
- Profitable in each of 2017, 2018, 2019 and 2020.
- WR target remains >=60%, but monthly cashflow/withdrawability is now measured directly rather than using trade count as a proxy.
- 2021+ remains sealed.

## Withdrawal models tested

### Hard retained-base model

At month-end, withdraw equity above RM100 and retain RM100. If the account is below RM100, withdraw RM0 and carry the reduced balance forward. No top-up.

This model produced too many long recovery periods. The best individual strategy reached only about 16/48 withdrawal months. A DD audit also found that resetting the high-water mark each month understated drawdown; the implementation was corrected so withdrawals reduce both equity and high-water mark while trading losses remain in the DD path.

### Rolling 50/50 model

This model is closer to the user's actual rolling objective:

1. Start with the existing account balance.
2. Risk 5% current equity per trade.
3. Stop taking new trades for the month as soon as the month becomes profitable relative to its starting balance.
4. At month-end, withdraw 50% of positive monthly P/L.
5. Retain the other 50% in the account to compound and repair future drawdowns.
6. Losing/flat month: RM0 withdrawal.
7. No capital top-up.
8. Cash withdrawals are removed from both balance and high-water mark for adjusted DD.

Workflow:
- `Historical First NY Rolling Cashflow`
- Run: `35868310720`
- Job: `107205481928`
- 6,912 strategy-policy combinations.
- Strict all-pass count: 0.

## Current best practical rolling candidate

Base strategy:

`NYCFAST__displacement__h4__NY_CASH_AM__deep705__A28__V1.15__L48`

### Trading rules

- Session: 09:30–12:30 New York local time, DST-aware.
- H4 directional bias uses completed H4 candles:
  - Long: H4 EMA20 > EMA50 and EMA20 slope over three H4 bars > 0.
  - Short: inverse.
- M5 displacement candle:
  - directional candle,
  - body >=0.55 ATR,
  - body/range >=0.65,
  - ADX >=28,
  - tick-volume ratio >=1.15,
  - close breaks the prior 48 M5-bar high/low.
- Pending entry at 70.5% retracement of the signal candle range.
- Pending order valid for 45 minutes.
- Stop beyond signal-candle wick plus 0.04 ATR.
- TP fixed at 3R.
- Maximum one entry per New York trading date.
- Same M5 TP+SL ambiguity: SL first.
- 1 bp round-trip cost.

### Base strategy quality

- Available trades: 69.
- Base WR: 44.93%.
- Expectancy: +0.565R/trade.
- PF: 1.83.

### Rolling 50/50 result

Monthly policy: stop trading after the month first becomes positive; withdraw 50% of positive month P/L and retain 50%.

- Trades actually used: 52.
- Withdrawal months: **25/48**.
- Withdrawal-month rate: **52.08%**.
- Longest no-withdrawal streak: **3 months**.
- Cash-flow-adjusted max DD: **23.61%**.
- Profitable calendar years: **4/4**.
- Total cash withdrawn: **RM168.01**.
- Median withdrawal in a withdrawal month: **RM7.52**.
- Minimum positive withdrawal: RM0.01.
- Worst monthly P/L: **-RM17.07**.
- Ending retained trading balance: **RM141.43**.
- Total economic value at end (withdrawals + retained balance): **RM309.44** from RM100 initial capital.

Yearly rolling cashflow:

| Year | Withdrawal months | Cash withdrawn | Sum monthly P/L | Used trades |
|---|---:|---:|---:|---:|
| 2017 | 6/12 | RM41.98 | +RM64.41 | 12 |
| 2018 | 6/12 | RM37.87 | +RM35.26 | 14 |
| 2019 | 6/12 | RM38.74 | +RM38.18 | 13 |
| 2020 | 7/12 | RM49.43 | +RM71.60 | 13 |

This candidate therefore passes:
- fixed 3R;
- 5% risk;
- real SL;
- NY-only;
- DD <=25%;
- profitable 2017–2020.

It does **not** pass:
- WR >=60% (actual 44.93%);
- withdrawal in every month (25/48, not 48/48).

## Secondary DD-compliant candidates

### H4+D1 displacement, L12

`NYCFAST__displacement__h4d1__NY_CASH_AM__deep705__A28__V1.15__L12`

- WR 40.98%.
- +0.398R/trade.
- PF 1.54.
- DD 21.90%.
- 22/48 withdrawal months.
- Longest dry streak 6 months.
- RM136.08 withdrawn.
- 4/4 profitable years.

### H4+D1 displacement, L48

`NYCFAST__displacement__h4d1__NY_CASH_AM__deep705__A28__V1.15__L48`

- WR 43.75%.
- +0.517R/trade.
- PF 1.74.
- DD 21.90%.
- 20/48 withdrawal months.
- Longest dry streak 6 months.
- RM136.71 withdrawn.
- 4/4 profitable years.

## Router / diversification finding

Simple multi-family routers raise monthly opportunity count and can raise withdrawal-month coverage, but the tested routers breached the 25% DD target.

A coarse search of staged/fallback combinations among independent NY families (displacement, EMA pullback, RSI2, previous-NY sweep, IB/ORB, overnight break, VWAP/FVG) did not beat the best individual displacement candidate while simultaneously keeping DD <=25% and all four years profitable.

Therefore the research should not add frequency blindly. The next search should explicitly optimize **monthly coverage conditional on risk**:

- primary high-quality displacement setup first;
- activate fallback setup only if the month is still not positive after a predefined point;
- stop for the month once a withdrawable profit is achieved;
- keep full real SL and 5% risk;
- reject any router that breaches 25% adjusted DD;
- keep WR as a reported hard target and do not manufacture it with protected stops.

## Current conclusion

The real bottleneck is now quantified correctly.

The best current strategy can generate a withdrawal in roughly half the development months while keeping adjusted DD below 25% and remaining profitable in all four development years.

However, **no strategy yet achieves the desired every-month withdrawal together with WR >=60%**.

The next research target is therefore not “more trades.” It is **increase withdrawal-month coverage from 25/48 toward 48/48 without exceeding 25% DD**, using causal fallback/rotation rules inside the New York session.

2021–2026 remains sealed until a development rule set is frozen.
