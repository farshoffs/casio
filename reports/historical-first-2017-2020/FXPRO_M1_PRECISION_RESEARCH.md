# FxPro XAUUSD M1 Precision Research — 2017–2020

## Data and protocol

Source supplied by user: `fxpro_xauusd_m1.csv`.

Observed file range:
- 2017-01-02 23:00 UTC through 2026-09-24 00:21 UTC.
- XAUUSD M1.
- OHLC + tick volume.

Development discipline:
- Only 2017-01-01 through 2020-12-31 was used for this research.
- 2021–2026 remains sealed.
- M5/H1/H4 bars are derived from the same FxPro M1 feed.
- New York time uses `America/New_York`, including DST.
- Fixed RR = 1:3.
- Risk model = 5% of current equity per entry, starting RM100.
- 1 bp round-trip cost.
- Real structural SL only.
- If SL and TP are both inside the same M1 bar, SL is applied first.
- Maximum one entry per New York trading date for this research.

## Families tested

1. Existing M5 displacement -> deep retracement, executed on M1.
2. M5 displacement -> M1 reclaim/MSS/engulf/FVG confirmation.
3. M1-native EMA pullback/reclaim.
4. M1-native overnight/premarket/previous-NY/opening-range sweep -> MSS.
5. Previous-NY sweep -> MSS -> deep retracement.
6. M1-native displacement -> deep retracement.
7. New York sub-session variants.

Main finding: M1 confirmation after the old weak displacement setup did not automatically raise WR. The strongest improvement came from using M1 for exact execution/fill sequencing while making the M5 displacement quality filter stricter.

# Strict-pass candidate: CASIO NY Precision v1

## Rules

Session:
- New York Cash AM only: 09:30–12:30 America/New_York.

Higher-timeframe bias:
- Completed H1 and H4 must align.
- Long: EMA20 > EMA50 and EMA20 3-bar slope > 0 on both H1 and H4.
- Short: inverse.

M5 setup:
- Directional displacement candle.
- ADX(14) >= 30.
- Tick volume ratio >= 1.15 versus M5 20-bar median.
- Candle body >= 0.80 ATR(14).
- Body/range >= 0.75.
- Long close breaks previous 16 M5-bar high.
- Short close breaks previous 16 M5-bar low.

Entry:
- After the M5 signal candle is fully closed, place a pending entry at 70.5% retracement of the completed signal-candle range.
- Order is valid for 15 minutes.
- Fill is resolved from M1 bars.

Stop:
- Long: below completed M5 signal low by 0.04 M5 ATR.
- Short: above completed M5 signal high by 0.04 M5 ATR.
- No breakeven/protected stop.

Target:
- Fixed 3R.

Execution:
- One entry maximum per NY date.
- One open position at a time.
- M1 same-bar ambiguity = stop first.
- 1 bp cost.

## Development / holdout validation

Parameter neighborhood was searched on 2017–2018, then the frozen rule was checked on 2019–2020 without changing the rule. **Audit caveat:** this is a robustness split / semi-holdout, not a pristine final OOS, because the displacement family and nearby parameter region had already been explored in earlier 2017–2020 research. True untouched forward validation remains 2021+.

### 2017–2018 selection segment
- Trades: 10
- WR: 60.00%
- Expectancy: +1.169R/trade
- Max DD: 11.78%
- Both years profitable.

### 2019–2020 holdout
- Trades: 16
- WR: 62.50%
- Expectancy: +1.320R/trade
- Max DD: 12.17%
- Both years profitable.

### Full 2017–2020
- Trades: 26
- Wins: 16
- Losses: 10
- WR: **61.54%**
- Expectancy: **+1.262R/trade**
- PF: **3.70**
- Max DD: **12.17%**
- Profitable years: **4/4**
- Continuous RM100 -> **RM437.68** before withdrawals.

Yearly:

| Year | Trades | WR | ExpR | PF | DD | RM100-reset ending |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 5 | 80.00% | +1.969 | 9.43 | 5.84% | RM157.74 |
| 2018 | 5 | 40.00% | +0.368 | 1.50 | 11.78% | RM107.10 |
| 2019 | 5 | 60.00% | +1.152 | 3.29 | 12.17% | RM129.40 |
| 2020 | 11 | 63.64% | +1.396 | 4.21 | 11.65% | RM200.21 |

Important: the >=60% WR target is met across the complete development sample and across the 2019–2020 robustness split. This must not be represented as final untouched OOS evidence. 2018 itself is only 40% WR, but remains profitable at fixed 3R.

# Neighbor stability

The result is not a single isolated parameter point.

A neighboring variant:
- H1+H4 alignment
- prior 16 M5 break
- ADX >= 28
- volume ratio >= 1.15
- body >= 0.80 ATR
- body/range >= 0.72
- 70.5% retrace
- 15-minute validity

Result:
- 30 trades
- WR 60.00%
- +1.206R/trade
- PF 3.50
- DD 12.17%
- 4/4 profitable years
- RM100 -> RM506.50
- Trades occurred in 25 distinct calendar months.

A focused 09:30–10:30 NY opening-hour variant also produced:
- 16 trades
- WR 68.75%
- +1.556R/trade
- PF 5.05
- DD 17.51%
- 4/4 profitable years.

This opening-hour result is exploratory and was identified after broader full-window exploration, so it should not replace the walk-forward-selected v1 rule without another validation step.

# Monthly withdrawal objective

The strict-pass trading quality does **not** yet solve the user's real cashflow objective.

Using the existing rolling 50/50 policy:
- stop taking new trades for the month once the month is positive;
- withdraw 50% of positive monthly P/L;
- retain 50% for rolling;
- no withdrawal in losing/flat months;

CASIO NY Precision v1 produced:
- Used trades: 23
- Used-trade WR: 65.22%
- Withdrawal months: **15/48**
- Longest no-withdrawal streak: **10 months**
- Total cash withdrawn: RM127.94
- Ending retained balance: RM173.60
- Adjusted DD: 11.78%
- 4/4 profitable years.

Therefore this system passes the statistical trading targets but **fails the every-month withdrawal objective**.

# Causal fallback experiment

A training-only fallback search was performed using a distinct previous-NY-liquidity family.

Frozen fallback rule:
- Only activate after calendar day 20 if the month is not yet positive.
- Maximum one fallback attempt in that month.
- H1+H4 aligned.
- Previous-NY high/low sweep.
- M1 MSS3 confirmation within 5 minutes.
- Confirmation body/range >= 0.60.
- Pending 70.5% retracement of confirmation candle.
- Limit valid 5 minutes.
- Stop beyond sweep-to-confirm structural extreme.
- Fixed 3R.

2017–2018 training router:
- Used trades 11
- WR 63.64%
- DD 6.32%
- Withdrawal months 7/24
- Both years profitable.

2019–2020 robustness-split router:
- Used trades 15
- WR 60.00%
- DD 11.65%
- Withdrawal months 9/24
- Both years profitable.

Full 2017–2020 router:
- Used trades 26
- WR 61.54%
- +1.260R/trade
- DD 12.38%
- Withdrawal months **16/48**
- Longest dry streak **5 months**
- 4/4 profitable years
- Total cash withdrawn RM132.74
- Ending retained balance RM163.20.

The fallback improves dry-streak behavior but does not solve monthly withdrawals.

# Rejected M1-native families

M1-native EMA pullbacks, overnight/premarket/opening-range sweep-MSS, and M1-native displacement did not meet the combined WR/DD/yearly target at meaningful sample sizes.

Previous-NY sweep -> MSS -> deep retracement improved precision, with several 4/4-positive variants and some 45–46% WR configurations, but meaningful-sample variants did not reach 60% WR.

Some 60–75% M1 confirmation variants existed only at 3–5 trades across four years and were rejected as insufficient evidence.

# Current conclusion

M1 materially improved the research.

For the first time, the historical development search has produced a multi-year fixed-3R system with:
- WR >=60%
- DD <=25%
- profitable in every year 2017–2020
- real structural SL
- 5% risk
- New York-only execution

without protected-SL manipulation.

However, the user's real objective is still not complete: withdrawal coverage is only 15/48 months for the single-rule system and 16/48 with the causal fallback router.

The next research problem is therefore no longer basic strategy quality. It is to discover additional **independent, high-precision New York setups** that fill currently empty months while preserving portfolio WR >=60% and DD <=25%.

2021–2026 remains sealed. The next legitimate validation step is to freeze the exact v1 rule first, then run it unchanged on 2021+ as true OOS.
