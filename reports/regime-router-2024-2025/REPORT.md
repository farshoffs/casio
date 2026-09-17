# Frozen CASIO Regime Router — 2024 & 2025

## Method

- Frozen exact Regime Router architecture from the 2026 ensemble test; no tuning on 2024/2025.
- Source: independent secondary XAUUSD M5 feed, resampled/processed identically to the 2026 research engine.
- Each annual test starts at **RM100** independently.
- Risk **5% of current account balance** per accepted trade.
- One shared portfolio position at a time.
- Same **1 bp round-trip cost**, stop-first same-bar handling, source-technique 2R/3R/4R target logic.
- Requirement: **at least 8 filled trades in every completed month** and ending balance above RM100.
- The continuous 2024->2025 row is an additional path test starting RM100 on 2024-01-01 without resetting in 2025.

## Results

| window               |   trades |   trades_per_30d |   min_completed_month_trades |   ending_balance_rm |   lowest_balance_rm | passes_frequency   | passes_growth   | requested_fit   |
|:---------------------|---------:|-----------------:|-----------------------------:|--------------------:|--------------------:|:-------------------|:----------------|:----------------|
| 2024                 |      433 |          35.4918 |                           31 |             6.85961 |             4.41133 | True               | False           | False           |
| 2025                 |      365 |          30      |                           19 |           975.673   |            97.4248  | True               | True            | True            |
| 2024-2025 continuous |      798 |          32.7497 |                           19 |            66.9274  |             4.41133 | True               | False           | False           |

## Monthly equity

| window               | month   |   trades |       pnl_rm |   ending_balance_rm |
|:---------------------|:--------|---------:|-------------:|--------------------:|
| 2024                 | 2024-01 |       31 |  -30.687     |            69.313   |
| 2024                 | 2024-02 |       34 |  -22.4197    |            46.8934  |
| 2024                 | 2024-03 |       35 |   21.9465    |            68.8399  |
| 2024                 | 2024-04 |       39 |  -31.8042    |            37.0357  |
| 2024                 | 2024-05 |       39 |  -19.1686    |            17.8671  |
| 2024                 | 2024-06 |       35 |   -7.80887   |            10.0582  |
| 2024                 | 2024-07 |       36 |   -1.84508   |             8.21316 |
| 2024                 | 2024-08 |       33 |   -0.451468  |             7.7617  |
| 2024                 | 2024-09 |       35 |    0.804258  |             8.56595 |
| 2024                 | 2024-10 |       42 |   -1.38661   |             7.17934 |
| 2024                 | 2024-11 |       34 |   -0.883196  |             6.29615 |
| 2024                 | 2024-12 |       40 |    0.563462  |             6.85961 |
| 2025                 | 2025-01 |       36 |   54.5406    |           154.541   |
| 2025                 | 2025-02 |       32 |    5.32188   |           159.862   |
| 2025                 | 2025-03 |       31 |  103.938     |           263.8     |
| 2025                 | 2025-04 |       36 |  174.293     |           438.093   |
| 2025                 | 2025-05 |       28 |  -85.5279    |           352.565   |
| 2025                 | 2025-06 |       29 |  130.31      |           482.875   |
| 2025                 | 2025-07 |       41 |    1.18016   |           484.055   |
| 2025                 | 2025-08 |       31 | -191.324     |           292.731   |
| 2025                 | 2025-09 |       19 |  150.252     |           442.983   |
| 2025                 | 2025-10 |       20 |  138.055     |           581.038   |
| 2025                 | 2025-11 |       28 |  -75.0228    |           506.015   |
| 2025                 | 2025-12 |       34 |  469.658     |           975.673   |
| 2024-2025 continuous | 2024-01 |       31 |  -30.687     |            69.313   |
| 2024-2025 continuous | 2024-02 |       34 |  -22.4197    |            46.8934  |
| 2024-2025 continuous | 2024-03 |       35 |   21.9465    |            68.8399  |
| 2024-2025 continuous | 2024-04 |       39 |  -31.8042    |            37.0357  |
| 2024-2025 continuous | 2024-05 |       39 |  -19.1686    |            17.8671  |
| 2024-2025 continuous | 2024-06 |       35 |   -7.80887   |            10.0582  |
| 2024-2025 continuous | 2024-07 |       36 |   -1.84508   |             8.21316 |
| 2024-2025 continuous | 2024-08 |       33 |   -0.451468  |             7.7617  |
| 2024-2025 continuous | 2024-09 |       35 |    0.804258  |             8.56595 |
| 2024-2025 continuous | 2024-10 |       42 |   -1.38661   |             7.17934 |
| 2024-2025 continuous | 2024-11 |       34 |   -0.883196  |             6.29615 |
| 2024-2025 continuous | 2024-12 |       40 |    0.563462  |             6.85961 |
| 2024-2025 continuous | 2025-01 |       36 |    3.74127   |            10.6009  |
| 2024-2025 continuous | 2025-02 |       32 |    0.36506   |            10.9659  |
| 2024-2025 continuous | 2025-03 |       31 |    7.12974   |            18.0957  |
| 2024-2025 continuous | 2025-04 |       36 |   11.9558    |            30.0515  |
| 2024-2025 continuous | 2025-05 |       28 |   -5.86688   |            24.1846  |
| 2024-2025 continuous | 2025-06 |       29 |    8.93873   |            33.1234  |
| 2024-2025 continuous | 2025-07 |       41 |    0.0809542 |            33.2043  |
| 2024-2025 continuous | 2025-08 |       31 |  -13.1241    |            20.0802  |
| 2024-2025 continuous | 2025-09 |       19 |   10.3067    |            30.3869  |
| 2024-2025 continuous | 2025-10 |       20 |    9.47004   |            39.8569  |
| 2024-2025 continuous | 2025-11 |       28 |   -5.14627   |            34.7107  |
| 2024-2025 continuous | 2025-12 |       34 |   32.2167    |            66.9274  |

## Interpretation

The router passes a window only when RM100 grows and every completed month contains at least 8 accepted trades. These are frozen-rule validation replays, not a new parameter search.
