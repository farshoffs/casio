# CASIO Native-M15 All-Strategy-Family Benchmark — 2026

## Test rule

- Source: `data/xauusd_m5_dukascopy_research.csv`, resampled to native M15 before signal logic.
- Test: **2026-01-01 through 2026-09-16T13:30:00+00:00**.
- Start **RM100** independently for every strategy.
- Risk **5% of current balance** per filled trade.
- User frequency target: **at least 8 filled trades in every completed month**.
- Reward target standardized to **2R / 3R / 4R depending on setup quality**.
- Cost: **1 bp round trip**. Same-bar stop/target collision is stop-first.
- Main judgment: does RM100 grow while satisfying the monthly trade floor?

## M15-0591 status

**M15-0591 is deliberately held aside. It is not rerun, modified, ranked, or used to define these translations.**

## Important comparability note

These are native-M15 translations of each historical CASIO strategy family, not claims of exact Pine/M5 parity. The point of this batch is to ask whether each strategy idea behaves differently when its execution timeframe is M15 under one common RM100/5%/2R-4R test.

Families/strategies tested: **18**. Requested-fit passes: **4**.

## Results

| strategy                 | family               |   trades |   trades_per_30d |   min_completed_month_trades |   ending_balance_rm |   lowest_balance_rm | passes_frequency   | passes_growth   | requested_fit   |
|:-------------------------|:---------------------|---------:|-----------------:|-----------------------------:|--------------------:|--------------------:|:-------------------|:----------------|:----------------|
| Outcome First M15        | Outcome First        |      121 |        14.0392   |                           10 |          419.596    |           94.9061   | True               | True            | True            |
| V1 Legacy M15            | Legacy               |      321 |        37.2444   |                           31 |          345.8      |           69.0675   | True               | True            | True            |
| Structural Frequency M15 | Structural Frequency |      113 |        13.1109   |                            8 |          237.784    |           93.3058   | True               | True            | True            |
| Structural Portfolio M15 | Structural Portfolio |      125 |        14.5033   |                           11 |          199.602    |           95.5419   | True               | True            | True            |
| Structural A+ M15        | Structural A+        |        8 |         0.928209 |                            0 |           95.2299   |           91.324    | False              | False           | False           |
| A+ M15                   | A+                   |        1 |         0.116026 |                            0 |           94.9053   |           94.9053   | False              | False           | False           |
| Route B Precision M15    | Route A/B            |        1 |         0.116026 |                            0 |           94.9053   |           94.9053   | False              | False           | False           |
| V5 Native M15            | V5                   |       28 |         3.24873  |                            0 |           92.4111   |           92.4111   | False              | False           | False           |
| V4 Confluence M15        | V4 Confluence        |      242 |        28.0783   |                           20 |           84.678    |           36.7455   | True               | False           | False           |
| V3 Trend M15             | V3                   |       16 |         1.85642  |                            0 |           73.4263   |           73.4263   | False              | False           | False           |
| V7 Momentum Alt M15      | V7 Momentum          |       79 |         9.16606  |                            6 |           52.8828   |           52.4772   | False              | False           | False           |
| Route A M15              | Route A/B            |      169 |        19.6084   |                           13 |           52.5861   |           28.9454   | True               | False           | False           |
| Structural Router M15    | Structural Router    |      217 |        25.1777   |                           19 |           16.1141   |           15.5153   | True               | False           | False           |
| V2 MTF M15               | V2                   |      272 |        31.5591   |                           24 |           10.8414   |            6.75499  | True               | False           | False           |
| V3 Range M15             | V3                   |      202 |        23.4373   |                           19 |            9.88601  |            7.54938  | True               | False           | False           |
| V3 Combined M15          | V3                   |      297 |        34.4598   |                           28 |            6.92216  |            5.26923  | True               | False           | False           |
| V6 Session Reaction M15  | V6                   |      299 |        34.6918   |                           29 |            0.620262 |            0.513959 | True               | False           | False           |
| V3 Asymmetry M15         | V3 Asymmetry         |      547 |        63.4663   |                           52 |            0.235883 |            0.218208 | True               | False           | False           |

## Top result under the user's test

**Outcome First M15**: RM100 -> **RM419.60**, 121 trades, minimum **10** trades in a completed month. Requested fit: **PASS**.

## Strategies that pass both conditions

| strategy                 |   trades |   min_completed_month_trades |   ending_balance_rm |   lowest_balance_rm |
|:-------------------------|---------:|-----------------------------:|--------------------:|--------------------:|
| Outcome First M15        |      121 |                           10 |             419.596 |             94.9061 |
| V1 Legacy M15            |      321 |                           31 |             345.8   |             69.0675 |
| Structural Frequency M15 |      113 |                            8 |             237.784 |             93.3058 |
| Structural Portfolio M15 |      125 |                           11 |             199.602 |             95.5419 |

## Translation inventory

| strategy                 | family               | translation                                                                   |
|:-------------------------|:---------------------|:------------------------------------------------------------------------------|
| Outcome First M15        | Outcome First        | FVG sweep or HTF-aligned displacement pullback.                               |
| V1 Legacy M15            | Legacy               | EMA trend + M15 10-bar breakout.                                              |
| Structural Frequency M15 | Structural Frequency | Looser displacement/retrace structural engine.                                |
| Structural Portfolio M15 | Structural Portfolio | Trend pullback + external sweep + expansion/retest playbooks.                 |
| Structural A+ M15        | Structural A+        | Structure + sweep + FVG + daily-auction alignment.                            |
| A+ M15                   | A+                   | Strict HTF alignment + fresh sweep + FVG + displacement.                      |
| Route B Precision M15    | Route A/B            | A+ precision subset: HTF + sweep + FVG + displacement + day-open alignment.   |
| V5 Native M15            | V5                   | V5 without M5 execution: H4/H1 context -> M15 sweep/BOS/FVG -> next M15 open. |
| V4 Confluence M15        | V4 Confluence        | Native-M15 confluence score: trend/BOS/FVG/sweep/ADX.                         |
| V3 Trend M15             | V3                   | HTF trend + recent M15 liquidity sweep + BOS.                                 |
| V7 Momentum Alt M15      | V7 Momentum          | One-bar M15 expansion-continuation variant; M15-0591 held aside and excluded. |
| Route A M15              | Route A/B            | Structural asymmetric engine; target graded 2R/3R/4R.                         |
| Structural Router M15    | Structural Router    | H4-ADX routes between trend continuation and sweep reversal.                  |
| V2 MTF M15               | V2                   | H4/H1 trend regime + M15 EMA20 pullback.                                      |
| V3 Range M15             | V3                   | Low-ADX Bollinger rejection / mean reversion.                                 |
| V3 Combined M15          | V3                   | Trend and range engines combined on M15.                                      |
| V6 Session Reaction M15  | V6                   | False-break reversal of completed Asia/London-morning ranges.                 |
| V3 Asymmetry M15         | V3 Asymmetry         | 20-bar liquidity sweep reversal with asymmetric 2R-4R target.                 |

## Interpretation

A PASS here means only that the fixed M15 translation satisfied the requested 2026 money/frequency test. It does not make the strategy proven outside this period. M15-0591 remains separate for later decision-making.
