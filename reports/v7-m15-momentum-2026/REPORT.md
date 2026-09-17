# CASIO v7 — Native M15 Volatility Expansion Momentum

This is a new native-M15 strategy family. M5 is used only as the source file and is resampled before any signal logic; all signals, entries, stops, targets and exits are evaluated on M15 bars.

## User test

- Start **RM100**.
- Risk **5% of current balance** per filled trade.
- Require **at least 8 trades in every completed month**.
- Judge primarily by where RM100 ends up.
- 1 bp round-trip cost assumption.

## New strategy logic

A large M15 expansion candle must break the high/low of a recent M15 range. Price then gets only a few M15 bars to make a controlled retracement into the impulse body and close back in the breakout direction. Entry is the next M15 open. Stop is beyond the impulse/pullback extreme; targets are fixed 2R, 3R or 4R. Same-bar stop/target collisions are stop-first.

## Find/test separation

- Discovery: secondary Octa/MT4 feed, 2024-01-01 through 2025-12-31.
- Untouched test: Dukascopy 2026-01-01 through 2026-09-16T13:30:00+00:00.
- Candidate rules searched: **864**.
- Discovery candidates meeting the monthly frequency floor: **214**.

## Best discovery candidates

| candidate   |   trades |   trades_per_30d |   min_month_trades |   end_rm |   lowest_rm |
|:------------|---------:|-----------------:|-------------------:|---------:|------------:|
| M15-0591    |      759 |          31.1491 |                 11 | 157.573  |     6.40153 |
| M15-0593    |      727 |          29.8358 |                 12 | 152.34   |     8.30487 |
| M15-0597    |      763 |          31.3133 |                 11 | 129.165  |     6.01201 |
| M15-0581    |      567 |          23.2695 |                 11 | 119.348  |    11.1088  |
| M15-0599    |      732 |          30.041  |                 12 | 117.855  |     7.79953 |
| M15-0579    |      581 |          23.844  |                 10 | 115.262  |     6.06204 |
| M15-0585    |      582 |          23.8851 |                 10 | 108.146  |     5.68782 |
| M15-0587    |      569 |          23.3516 |                 11 | 105.685  |    10.423   |
| M15-0615    |      727 |          29.8358 |                 10 | 104.957  |     7.24509 |
| M15-0617    |      699 |          28.6867 |                 11 | 101.789  |    10.7971  |
| M15-0305    |      854 |          35.0479 |                 16 |  96.4654 |     3.19404 |
| M15-0303    |      893 |          36.6484 |                 15 |  89.4057 |     1.78646 |
| M15-0621    |      731 |          30      |                 10 |  86.0349 |     6.80423 |
| M15-0311    |      859 |          35.2531 |                 16 |  81.87   |     2.99969 |
| M15-0309    |      897 |          36.8126 |                 15 |  80.3988 |     1.72593 |
| M15-0623    |      704 |          28.8919 |                 11 |  78.7468 |    10.1401  |
| M15-0641    |      657 |          26.9631 |                 10 |  69.5464 |     6.50283 |
| M15-0605    |      541 |          22.2025 |                 10 |  66.22   |    12.0789  |
| M15-0639    |      684 |          28.0711 |                 10 |  62.6889 |     4.55846 |
| M15-0611    |      543 |          22.2845 |                 10 |  58.6388 |    11.3333  |

## Frozen finalists on Dukascopy 2026

| candidate   |   trades |   trades_per_30d |   min_month_trades |   end_rm |   lowest_rm | passes_monthly_frequency   |   discovery_end_rm |
|:------------|---------:|-----------------:|-------------------:|---------:|------------:|:---------------------------|-------------------:|
| M15-0605    |      190 |          22.045  |                 13 |  648.243 |     56.6643 | True                       |            66.22   |
| M15-0611    |      190 |          22.045  |                 13 |  648.243 |     56.6643 | True                       |            58.6388 |
| M15-0647    |      228 |          26.454  |                 19 |  472.307 |     37.6249 | True                       |            53.8031 |
| M15-0581    |      204 |          23.6693 |                 15 |  421.094 |     45.3476 | True                       |           119.348  |
| M15-0587    |      204 |          23.6693 |                 15 |  421.094 |     45.3476 | True                       |           105.685  |
| M15-0599    |      255 |          29.5867 |                 21 |  395.627 |     29.6553 | True                       |           117.855  |
| M15-0623    |      241 |          27.9623 |                 19 |  361.417 |     38.4608 | True                       |            78.7468 |
| M15-0329    |      291 |          33.7636 |                 24 |  352.059 |     34.3704 | True                       |            52.5982 |
| M15-0311    |      305 |          35.388  |                 25 |  337.033 |     31.5831 | True                       |            81.87   |
| M15-0641    |      226 |          26.2219 |                 18 |  329.373 |     31.4001 | True                       |            69.5464 |
| M15-0305    |      303 |          35.1559 |                 25 |  297.59  |     31.5831 | True                       |            96.4654 |
| M15-0621    |      249 |          28.8905 |                 20 |  293.401 |     39.7545 | True                       |            86.0349 |
| M15-0593    |      253 |          29.3546 |                 20 |  275.899 |     24.749  | True                       |           152.34   |
| M15-0645    |      238 |          27.6142 |                 20 |  269.099 |     38.4539 | True                       |            51.3871 |
| M15-0617    |      239 |          27.7302 |                 18 |  252.042 |     32.0977 | True                       |           101.789  |
| M15-0597    |      265 |          30.7469 |                 22 |  250.393 |     29.0454 | True                       |           129.165  |
| M15-0579    |      213 |          24.7136 |                 16 |  247.183 |     45.8859 | True                       |           115.262  |
| M15-0585    |      213 |          24.7136 |                 16 |  247.183 |     45.8859 | True                       |           108.146  |
| M15-0615    |      247 |          28.6584 |                 19 |  222.83  |     34.622  | True                       |           104.957  |
| M15-0639    |      236 |          27.3822 |                 19 |  204.373 |     33.4894 | True                       |            62.6889 |
| M15-0591    |      263 |          30.5149 |                 21 |  190.166 |     25.2955 | True                       |           157.573  |
| M15-0309    |      322 |          37.3604 |                 27 |  168.891 |     25.5237 | True                       |            80.3988 |
| M15-0327    |      308 |          35.736  |                 26 |  159.426 |     24.2948 | True                       |            54.8542 |
| M15-0303    |      320 |          37.1284 |                 27 |  155.628 |     25.5237 | True                       |            89.4057 |

## Primary candidate — selected before 2026

Candidate **M15-0591**
- 2024-2025 discovery: RM100 -> **RM157.57**.
- Dukascopy 2026: RM100 -> **RM190.17**.
- 2026 trades: **263**, equivalent to **30.51/30d**.
- Minimum trades among completed 2026 months: **21**.
- Lowest 2026 balance: **RM25.30**.
- Frequency requirement: **PASS**.
- RM100 growth requirement: **PASS**.
- Overall requested fit: **PASS**.

### Frozen rules

```json
{
  "body_min": 0.55,
  "breakout_buffer_atr": 0.0,
  "impulse_atr": 1.2,
  "lookback": 20,
  "max_hold_bars": 40,
  "max_risk_atr": 2.8,
  "min_risk_atr": 0.35,
  "pullback_bars": 4,
  "retrace_max": 0.5,
  "session": "ALL",
  "stop_buffer_atr": 0.12,
  "target_r": 3.0
}
```

### 2026 month-by-month balance

| month   |   trades |   pnl_rm |   ending_balance_rm |
|:--------|---------:|---------:|--------------------:|
| 2026-01 |       30 |  31.9605 |            131.96   |
| 2026-02 |       21 | -59.7464 |             72.2141 |
| 2026-03 |       32 | -14.0788 |             58.1353 |
| 2026-04 |       33 | -30.5759 |             27.5594 |
| 2026-05 |       31 |  37.254  |             64.8134 |
| 2026-06 |       34 |  80.0577 |            144.871  |
| 2026-07 |       33 | -18.439  |            126.432  |
| 2026-08 |       34 |  84.0099 |            210.442  |
| 2026-09 |       15 | -20.2757 |            190.166  |

## Exploratory best 2026 finalist

This is exploratory because it is chosen after comparing 2026 finalists; it is not an untouched selection.

Candidate **M15-0605**: RM100 -> **RM648.24**, with minimum completed-month frequency **13**.