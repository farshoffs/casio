# Bermula H4 Direction -> M15 Setup -> M1 Entry
## Full-history validation: 2017-2026 YTD

Updated: 2026-09-24

### Scope

This extends the exact corrected 2026 engine without changing the rules:

```text
H4 Bermula / S&R break -> direction only
M15 Bermula / S&R -> actual setup
M15 strong breakout -> pullback / role reversal
M1 micro confirmation -> entry
M15 Bermula structural stop
Fixed-R target
One position at a time
```

Source: user-supplied FxPro XAUUSD M1 CSV.

Data range: 2017-01-02 23:00 UTC through 2026-09-24 00:21 UTC.

Important: the file contains no pre-2017 history. Therefore 2017 has a causal warm-up period. The first usable H4 direction state appears on 2017-03-02 and the first entry is 2017-03-10. 2026 is YTD through September 24.

No session filter is imposed. No RM100 / account-risk rule is used to select signals. RM100 compounding is reported separately.

### Reproduction check

Before accepting any 2017-2025 result, the rebuilt long-history engine was required to reproduce the existing 2026 fingerprint.

It does so exactly:

| RR | 2026 trades | WR | Net R | Max DD | Max loss streak |
|---:|---:|---:|---:|---:|---:|
| 0.5R | 70 | 74.29% | +8.0R | 3.5R | 3 |
| 0.8R | 69 | 65.22% | +12.0R | 3.8R | 3 |
| 1.0R | 69 | 57.97% | +11.0R | 6.0R | 3 |
| 1.5R | 69 | 44.93% | +8.5R | 6.0R | 6 |
| 2.0R | 63 | 39.68% | +12.0R | 9.0R | 7 |
| 3.0R | 57 | 29.82% | +11.0R | 10.0R | 10 |
| 5.4R | 50 | 20.00% | +14.0R | 14.0R | 14 |

The 2026 signal funnel also reproduces the prior result: 158 H4-direction-aligned M15 breakout events -> 132 pullbacks -> 74 M1 confirmations -> 72 unique signals.

### Full-history signal funnel

Across the complete file:

- H4 Bermula origin zones: 411
- strong H4 direction-state events: 195
- M15 Bermula origin zones: 5,731
- H4-direction-aligned strong M15 breakouts: 1,933
- pullbacks / retests: 1,503
- M1 confirmations: 847
- unique confirmed signals after exact-minute deduplication: 800

### Full-history fixed-R results

| RR | Trades | Wins | Losses | WR | Gross net R | Exp/trade | PF | Max DD R | Max loss streak |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5R | 786 | 518 | 268 | 65.90% | -9.0R | -0.011R | 0.966 | 32.0R | 5 |
| 0.8R | 780 | 433 | 347 | 55.51% | -0.6R | -0.001R | 0.998 | 36.0R | 5 |
| 1.0R | 775 | 384 | 391 | 49.55% | -7.0R | -0.009R | 0.982 | 44.0R | 7 |
| 1.5R | 762 | 293 | 469 | 38.45% | -29.5R | -0.039R | 0.937 | 53.0R | 11 |
| 2.0R | 743 | 249 | 494 | 33.51% | +4.0R | +0.005R | 1.008 | 32.0R | 12 |
| **3.0R** | **694** | **183** | **511** | **26.37%** | **+38.0R** | **+0.055R** | **1.074** | **25.0R** | **14** |
| 5.4R | 633 | 103 | 530 | 16.27% | +26.2R | +0.041R | 1.049 | 44.6R | 20 |

The 2026-preferred 0.8R exit does **not** generalize across the full history. Gross performance over 2017-2026 is essentially flat.

Among the predeclared exits, 3R has the strongest full-history gross result and the smallest gross R drawdown among the positive high-R variants. This is a descriptive in-sample comparison, not a final parameter selection.

### 0.8R by year

| Year | Trades | WR | Gross R | Max DD R | 1bp sensitivity R |
|---:|---:|---:|---:|---:|---:|
| 2017* | 74 | 54.05% | -2.0 | 13.0 | -8.28 |
| 2018 | 85 | 56.47% | +1.4 | 7.2 | -5.10 |
| 2019 | 87 | 52.87% | -4.2 | 9.0 | -10.44 |
| 2020 | 71 | 43.66% | -15.2 | 16.8 | -18.17 |
| 2021 | 87 | 63.22% | +12.0 | 9.0 | +7.41 |
| 2022 | 87 | 50.57% | -7.8 | 16.0 | -12.38 |
| 2023 | 72 | 61.11% | +7.2 | 10.2 | +2.41 |
| 2024 | 77 | 49.35% | -8.6 | 14.0 | -12.72 |
| 2025 | 71 | 59.15% | +4.6 | 3.0 | +1.62 |
| 2026** | 69 | 65.22% | +12.0 | 3.8 | +10.14 |

*2017 has no pre-2017 warm-up history. **2026 is YTD.

### 3R by year

| Year | Trades | WR | Gross R | Max DD R | Loss streak | 1bp sensitivity R |
|---:|---:|---:|---:|---:|---:|---:|
| 2017* | 67 | 25.37% | +1 | 16 | 11 | -4.71 |
| 2018 | 80 | 26.25% | +4 | 11 | 10 | -2.20 |
| 2019 | 78 | 25.64% | +2 | 11 | 10 | -3.72 |
| 2020 | 64 | 23.44% | -4 | 12 | 9 | -6.70 |
| 2021 | 76 | 30.26% | +16 | 13 | 12 | +11.95 |
| 2022 | 77 | 20.78% | -13 | 21 | 13 | -16.89 |
| 2023 | 62 | 29.03% | +10 | 13 | 8 | +5.96 |
| 2024 | 66 | 24.24% | -2 | 12 | 12 | -5.62 |
| 2025 | 67 | 29.85% | +13 | 9 | 8 | +10.17 |
| 2026** | 57 | 29.82% | +11 | 10 | 10 | +9.50 |

Gross: 7 of 10 calendar-year rows are positive at 3R, but several early-year gains are extremely thin.

### Execution-cost sensitivity

The M1 CSV has a single OHLC stream and no bid/ask spread series, so actual historical execution cost cannot be reconstructed.

A deliberately simple 1-basis-point round-trip price-cost sensitivity was applied exactly as in the 2026 research.

Over the full period:

- 0.8R: -0.6R gross -> **-45.50R** at 1bp sensitivity
- 1R: -7R -> **-51.57R**
- 2R: +4R -> **-38.99R**
- 3R: +38R -> **-2.26R**
- 5.4R: +26.2R -> **-10.69R**

The average 1bp cost is about 0.058R/trade because M15 structural stops can be tight.

Therefore the long-term gross 3R edge is too small to call robust without real spread/slippage data.

### RM100 compounding

Using current-equity percentage risk and gross trade results:

| RR | RM100 @ 1% risk | Max DD % | RM100 @ 2% risk | Max DD % | RM100 @ 5% risk | Max DD % |
|---:|---:|---:|---:|---:|---:|---:|
| 0.8R | RM96.34 | 31.1% | RM87.18 | 53.8% | RM44.21 | 88.1% |
| 1R | RM89.70 | 36.6% | RM74.45 | 61.0% | RM26.71 | 92.5% |
| 2R | RM96.66 | 30.5% | RM80.72 | 55.6% | RM20.06 | 93.7% |
| **3R** | **RM131.46** | **22.6%** | **RM140.44** | **42.5%** | **RM53.02** | **87.1%** |
| 5.4R | RM109.46 | 39.5% | RM86.58 | 67.3% | RM7.68 | 97.7% |

This illustrates geometric volatility drag. A strategy can have positive additive R and still shrink an account when the percentage risk per trade is too high.

At 3R:
- 1% current-equity risk grows RM100 to about RM131.46 gross;
- 2% grows it to about RM140.44 gross, but with ~42.5% max equity drawdown;
- 5% ends at only about RM53.02 despite +38 additive R, because long losing sequences cause severe geometric damage.

With the 1bp sensitivity included, even 3R ends around:
- RM87.87 at 1% risk;
- RM62.68 at 2%;
- RM6.96 at 5%.

Again, 1bp is a sensitivity, not measured FxPro spread.

### Frequency

The system does not produce eight trades every month under this native all-session implementation.

At 0.8R, average frequency is 6.67 trades/month, median 7; 76 of 117 calendar months have fewer than 8 trades.

At 3R, average frequency is 5.93 trades/month, median 6; 88 of 117 months have fewer than 8 trades. Longer targets keep the one-position-at-a-time engine occupied and therefore skip more later signals.

### Conclusion

The full-history extension rejects the idea that the excellent 2026 0.8R result is sufficient evidence of a durable exit.

The corrected H4-direction -> M15-Bermula -> M1-confirmation architecture is mechanically reproducible and generates many setups, but the long-run edge is weak and regime-dependent under the current deterministic translation.

3R is the most promising of the already-predeclared gross exits over the full sample, but its margin is not robust to the simple 1bp execution-cost sensitivity.

The next useful research task is not to tune RR on the same data. It is to improve setup quality using creator-native Bermula filters / confirmation definitions and then validate on held-out years.
