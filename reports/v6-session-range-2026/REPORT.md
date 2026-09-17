# CASIO v6 — Adaptive Session Range Reaction

This is a **new strategy family**, not a retune of Structural Portfolio, Route A/B, v3, v4 or v5.

## Test rule

Start **RM100**, risk **5% of current balance per trade**, require **>= 8 trades/month**, and judge the result by ending balance.

## Strategy idea

- London trades reactions to the completed Asia 00:00-06:00 UTC range.
- New York trades reactions to the completed London-morning 07:00-12:00 UTC range.
- REVERSAL mode fades false breaks that return inside the completed range.
- BREAKOUT mode waits for a break and retest from outside the completed range.
- ADAPTIVE mode uses the current session-range size versus its trailing 20-session median: compressed ranges use breakout/retest; expanded ranges use false-break reversal.
- Entries occur on the **next bar** after confirmation. Same-bar stop/target collisions are stop-first.
- Targets are fixed or dynamic **2R-4R**. Round-trip cost assumption: **1 bp**.

## Find vs test separation

- Rule search: Octa/MT4 secondary feed, 2024-01-01 through 2025-12-31.
- Untouched test: Dukascopy, 2026-01-01 through 2026-09-16T13:30:00+00:00.
- Candidates searched: **1440**. Frequency-qualified discovery candidates: **128**.

## Best discovery candidates

| candidate   |   trades |   trades_per_30d |   min_month_trades |   end_rm |   lowest_rm |
|:------------|---------:|-----------------:|-------------------:|---------:|------------:|
| V6-0245     |      544 |          22.3256 |                  8 |  48.7059 |    14.6968  |
| V6-0253     |      544 |          22.3256 |                  8 |  48.7059 |    14.6968  |
| V6-0249     |      545 |          22.3666 |                  8 |  41.9277 |    14.736   |
| V6-0241     |      545 |          22.3666 |                  8 |  41.9277 |    14.736   |
| V6-1193     |      529 |          21.71   |                  8 |  40.1154 |     8.91363 |
| V6-1213     |      452 |          18.5499 |                  8 |  37.8784 |    18.2171  |
| V6-1161     |      554 |          22.736  |                  8 |  36.4656 |     6.00355 |
| V6-1205     |      422 |          17.3187 |                  8 |  35.867  |    15.963   |
| V6-1209     |      453 |          18.591  |                  8 |  35.6441 |    15.8209  |
| V6-1181     |      479 |          19.658  |                  8 |  31.983  |    10.956   |
| V6-1198     |      528 |          21.6689 |                  8 |  31.7067 |     3.5069  |
| V6-1197     |      529 |          21.71   |                  8 |  30.7346 |     7.16281 |
| V6-1173     |      449 |          18.4268 |                  8 |  30.2847 |     9.60038 |
| V6-1201     |      423 |          17.3598 |                  8 |  29.4775 |    12.9316  |
| V6-1177     |      480 |          19.699  |                  8 |  29.4505 |    10.5137  |
| V6-1214     |      450 |          18.4679 |                  8 |  29.1115 |    12.2182  |
| V6-0221     |      574 |          23.5568 |                  8 |  29.1062 |     7.16314 |
| V6-0213     |      574 |          23.5568 |                  8 |  29.1062 |     7.16314 |
| V6-1165     |      554 |          22.736  |                  8 |  28.462  |     4.51258 |
| V6-1166     |      552 |          22.6539 |                  8 |  27.9111 |     2.26123 |

## Frozen finalists on Dukascopy 2026

| candidate   |   trades |   trades_per_30d |   min_month_trades |   end_rm |   lowest_rm |   discovery_end_rm |
|:------------|---------:|-----------------:|-------------------:|---------:|------------:|-------------------:|
| V6-1166     |      174 |          20.1885 |                 12 |  30.8142 |     20.7843 |            27.9111 |
| V6-1161     |      176 |          20.4206 |                 12 |  27.9311 |     21.3382 |            36.4656 |
| V6-1198     |      169 |          19.6084 |                 12 |  22.7373 |     17.5334 |            31.7067 |
| V6-1165     |      175 |          20.3046 |                 12 |  21.7767 |     16.4521 |            28.462  |
| V6-1193     |      171 |          19.8405 |                 12 |  20.3583 |     16.2071 |            40.1154 |
| V6-1209     |      146 |          16.9398 |                  9 |  20.2865 |     16.2098 |            35.6441 |
| V6-0213     |      190 |          22.045  |                 12 |  19.7027 |     17.8681 |            29.1062 |
| V6-0221     |      190 |          22.045  |                 12 |  19.7027 |     17.8681 |            29.1062 |
| V6-1177     |      153 |          17.752  |                 10 |  18.6825 |     14.9282 |            29.4505 |
| V6-1213     |      145 |          16.8238 |                  8 |  18.1532 |     14.4944 |            37.8784 |
| V6-1201     |      137 |          15.8956 |                  7 |  17.4693 |     13.9587 |            29.4775 |
| V6-1181     |      152 |          17.636  |                  9 |  16.7312 |     13.359  |            31.983  |
| V6-1214     |      144 |          16.7078 |                  8 |  16.7257 |     12.2433 |            29.1115 |
| V6-1197     |      170 |          19.7244 |                 12 |  15.8607 |     12.6177 |            30.7346 |
| V6-0253     |      186 |          21.5809 |                 12 |  15.714  |     14.3466 |            48.7059 |
| V6-0245     |      186 |          21.5809 |                 12 |  15.714  |     14.3466 |            48.7059 |
| V6-1205     |      137 |          15.8956 |                  7 |  15.5745 |     12.4354 |            35.867  |
| V6-1173     |      143 |          16.5917 |                  8 |  15.1523 |     12.0984 |            30.2847 |
| V6-0241     |      186 |          21.5809 |                 12 |  14.9916 |     13.6937 |            41.9277 |
| V6-0249     |      186 |          21.5809 |                 12 |  14.9916 |     13.6937 |            41.9277 |

## Primary candidate — selected before 2026 was inspected

Candidate **V6-0245**
- 2024-2025 discovery: RM100 -> **RM48.71**.
- Dukascopy 2026: RM100 -> **RM15.71**.
- Trades: **186**, equivalent to **21.58/30d**.
- Minimum trades among completed 2026 months: **14**.
- Lowest balance reached: **RM14.35**.
- Frequency requirement: **PASS**.
- RM100 growth requirement: **FAIL**.
- Overall requested fit: **FAIL**.

### Frozen rules

```json
{
  "body_min": 0.55,
  "excursion_atr": 0.1,
  "mode": "REVERSAL",
  "range_ratio_cut": 1.0,
  "retest_bars": 4,
  "sessions": "BOTH",
  "stop_buffer_atr": 0.16,
  "target_scheme": "FIXED2"
}
```

### 2026 month-by-month balance

| month   |   trades |    pnl_rm |   ending_balance_rm |
|:--------|---------:|----------:|--------------------:|
| 2026-01 |       21 | -12.2187  |             87.7813 |
| 2026-02 |       14 |  35.8313  |            123.613  |
| 2026-03 |       19 | -16.5965  |            107.016  |
| 2026-04 |       25 | -29.5328  |             77.4832 |
| 2026-05 |       24 | -40.0092  |             37.474  |
| 2026-06 |       22 | -13.8967  |             23.5774 |
| 2026-07 |       23 |  -1.83652 |             21.7409 |
| 2026-08 |       26 |  -2.16608 |             19.5748 |
| 2026-09 |       12 |  -3.86081 |             15.714  |

The selection criterion is not PF or win rate. It is the user's requested equity-first test: frequency plus RM100 ending balance.