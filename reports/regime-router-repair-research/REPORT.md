# CASIO Regime Router — Interpretable Repair Research

## Rules

- BASELINE: frozen 2026 Regime Router logic.
- NO_DOUBLE_OPPOSE: never accept a trade when completed H1 and H4 both point against its direction.
- LONDON_CONSENSUS: NO_DOUBLE_OPPOSE plus every London trade needs agreement from >=2 techniques in the prior 30 minutes.
- NARROW_CONFIRM: NO_DOUBLE_OPPOSE plus Structural Portfolio needs confirmation in London and V1 shorts need confirmation everywhere.
- COMBINED_GUARD: NARROW_CONFIRM plus >=1 ATR London bars need >=2-technique agreement.
- No numerical threshold grid search was performed; these are hypotheses derived from the 2024 diagnostic concentration.

## Full comparison

|   year | feed      | variant          |   trades |   trades_per_30d |   min_completed_month_trades |   ending_balance_rm |   lowest_balance_rm |   max_drawdown_pct | passes_frequency   | passes_growth   | requested_fit   |
|-------:|:----------|:-----------------|---------:|-----------------:|-----------------------------:|--------------------:|--------------------:|-------------------:|:-------------------|:----------------|:----------------|
|   2024 | secondary | BASELINE         |      433 |          35.4918 |                           31 |             6.85961 |             4.41133 |            96.1186 | True               | False           | False           |
|   2024 | secondary | NO_DOUBLE_OPPOSE |      425 |          34.8361 |                           30 |            10.6745  |             6.10587 |            94.6276 | True               | False           | False           |
|   2024 | secondary | LONDON_CONSENSUS |      360 |          29.5082 |                           26 |            25.4226  |            11.0002  |            88.9998 | True               | False           | False           |
|   2024 | secondary | NARROW_CONFIRM   |      404 |          33.1148 |                           27 |            18.9453  |            10.8172  |            90.4512 | True               | False           | False           |
|   2024 | secondary | COMBINED_GUARD   |      381 |          31.2295 |                           25 |            26.3495  |            12.9593  |            87.0407 | True               | False           | False           |
|   2025 | secondary | BASELINE         |      365 |          30      |                           19 |          1056.18    |            97.4248  |            58.0476 | True               | True            | True            |
|   2025 | secondary | NO_DOUBLE_OPPOSE |      361 |          29.6712 |                           19 |          1080.73    |            97.4248  |            55.7258 | True               | True            | True            |
|   2025 | secondary | LONDON_CONSENSUS |      310 |          25.4795 |                           18 |           328.225   |            84.2747  |            77.4319 | True               | True            | True            |
|   2025 | secondary | NARROW_CONFIRM   |      348 |          28.6027 |                           18 |          1859.36    |            97.4248  |            46.9411 | True               | True            | True            |
|   2025 | secondary | COMBINED_GUARD   |      322 |          26.4658 |                           18 |           868.541   |           100       |            68.6367 | True               | True            | True            |
|   2026 | dukascopy | BASELINE         |      284 |          32.9514 |                           22 |           842.285   |            75.4496  |            48.2478 | True               | True            | True            |
|   2026 | dukascopy | NO_DOUBLE_OPPOSE |      278 |          32.2553 |                           22 |          1038.85    |            75.4496  |            48.2478 | True               | True            | True            |
|   2026 | dukascopy | LONDON_CONSENSUS |      237 |          27.4982 |                           20 |           863.25    |            94.9151  |            41.8935 | True               | True            | True            |
|   2026 | dukascopy | NARROW_CONFIRM   |      255 |          29.5867 |                           19 |           818.135   |            75.4496  |            48.2609 | True               | True            | True            |
|   2026 | dukascopy | COMBINED_GUARD   |      236 |          27.3822 |                           18 |           629.914   |            93.3058  |            42.4965 | True               | True            | True            |

## RM100 ending balance by year

| variant          |     2024 |     2025 |     2026 |
|:-----------------|---------:|---------:|---------:|
| BASELINE         |  6.85961 | 1056.18  |  842.285 |
| COMBINED_GUARD   | 26.3495  |  868.541 |  629.914 |
| LONDON_CONSENSUS | 25.4226  |  328.225 |  863.25  |
| NARROW_CONFIRM   | 18.9453  | 1859.36  |  818.135 |
| NO_DOUBLE_OPPOSE | 10.6745  | 1080.73  | 1038.85  |

## Minimum trades in any completed month

| variant          |   2024 |   2025 |   2026 |
|:-----------------|-------:|-------:|-------:|
| BASELINE         |     31 |     19 |     22 |
| COMBINED_GUARD   |     25 |     18 |     18 |
| LONDON_CONSENSUS |     26 |     18 |     20 |
| NARROW_CONFIRM   |     27 |     18 |     19 |
| NO_DOUBLE_OPPOSE |     30 |     19 |     22 |

## Requested-fit PASS by year

| variant          | 2024   | 2025   | 2026   |
|:-----------------|:-------|:-------|:-------|
| BASELINE         | False  | True   | True   |
| COMBINED_GUARD   | False  | True   | True   |
| LONDON_CONSENSUS | False  | True   | True   |
| NARROW_CONFIRM   | False  | True   | True   |
| NO_DOUBLE_OPPOSE | False  | True   | True   |

A repair is only interesting if it improves the 2024 failure without collapsing 2025/2026 or the >=8-trades-per-month rule. 2023 Dukascopy remains the next genuinely older validation window.
