# CASIO — All Backtestable Strategies, 2026 Dukascopy RM100

Dataset: `data/xauusd_m5_dukascopy_research.csv`. Counted entry window: **2026-01-01 UTC → 2026-09-16T13:30:00+00:00**. Pre-2026 bars from 2025-10-01 are used only for causal warm-up.

## Common money assumptions

- Starting balance: **RM100 per strategy**, reset independently for every strategy/variant.
- Risk: **5% of current equity per filled trade**, compounded trade by trade.
- Stop-first handling is retained where the underlying replay defines same-bar stop/target collisions.
- Most v3/structural engines include the repository's **1.0 bps round-trip** cost model. Legacy and v4 Python replays do not explicitly deduct transaction costs; that difference is shown in the Cost column.
- This job does **not** optimize parameters on 2026. It replays the fixed named strategies/profiles already present in CASIO.

Backtested fixed strategies/variants: **81**.

## 2026 comparison

| Strategy | Family | Trades | Trades/30d | WR | Avg W | Avg L | Exp R | PF | Net R | End RM | Return | Max DD | 8/mo+70 | Cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Structural Portfolio 3.5R | Structural Portfolio | 38 | 4.41 | 34.21% | 3.36 | 1.06 | 0.453 | 1.65 | 17.22 | 193.18 | 93.18% | 31.56% | NO | 1.0 bps round trip |
| Legacy Python Regime Router | Legacy | 785 | 91.08 | 41.15% | 1.57 | 1.00 | 0.056 | 1.09 | 43.83 | 185.45 | 85.45% | 90.40% | NO | no explicit transaction cost in legacy replay |
| Structural Frequency STRICT_FVG | Structural Frequency | 39 | 4.53 | 33.33% | 3.36 | 1.06 | 0.415 | 1.59 | 16.19 | 183.18 | 83.18% | 35.10% | NO | 1.0 bps round trip |
| V3 Classic M15 Only | V3 M5 | 4 | 0.46 | 50.00% | 2.96 | 1.01 | 0.974 | 2.92 | 3.90 | 118.79 | 18.79% | 9.88% | NO | 1.0 bps round trip |
| V3 M5 Combined | V3 M5 | 131 | 15.20 | 34.35% | 2.21 | 1.03 | 0.078 | 1.12 | 10.26 | 114.77 | 14.77% | 70.73% | NO | 1.0 bps round trip |
| Outcome First RETEST_BODY | Outcome First | 7 | 0.81 | 28.57% | 3.43 | 1.05 | 0.229 | 1.30 | 1.60 | 104.76 | 4.76% | 19.41% | NO | 1.0 bps round trip |
| Route A Structural Asymmetric | Route A/B | 94 | 10.91 | 30.85% | 2.57 | 1.05 | 0.071 | 1.10 | 6.65 | 100.67 | 0.67% | 69.41% | NO | 1.0 bps round trip |
| V3 M5 Range Only | V3 M5 | 0 | 0.00 | 0.00% | — | — | 0.000 | — | 0.00 | 100.00 | 0.00% | 0.00% | NO | 1.0 bps round trip |
| Structural Frequency FULL_STRUCTURAL_ROUTER | Structural Frequency | 89 | 10.33 | 25.84% | 3.33 | 1.05 | 0.085 | 1.11 | 7.56 | 99.02 | -0.98% | 68.67% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | Structural A+ | 7 | 0.81 | 28.57% | 2.45 | 1.08 | -0.067 | 0.91 | -0.47 | 95.46 | -4.54% | 15.02% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | Structural A+ | 7 | 0.81 | 28.57% | 2.45 | 1.08 | -0.067 | 0.91 | -0.47 | 95.46 | -4.54% | 15.02% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | Structural A+ | 7 | 0.81 | 28.57% | 2.45 | 1.08 | -0.067 | 0.91 | -0.47 | 95.46 | -4.54% | 15.02% | NO | 1.0 bps round trip |
| V3 Asymmetry balanced_3_5r | V3 Asymmetry | 10 | 1.16 | 20.00% | 4.29 | 1.06 | 0.011 | 1.01 | 0.11 | 95.36 | -4.64% | 23.59% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB4 FULL_3_5R | Structural A+ | 7 | 0.81 | 28.57% | 2.39 | 1.08 | -0.085 | 0.89 | -0.59 | 94.91 | -5.09% | 15.02% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB6 FULL_3_5R | Structural A+ | 7 | 0.81 | 28.57% | 2.39 | 1.08 | -0.085 | 0.89 | -0.59 | 94.91 | -5.09% | 15.02% | NO | 1.0 bps round trip |
| Structural A+ R4.0 RB8 FULL_3_5R | Structural A+ | 7 | 0.81 | 28.57% | 2.39 | 1.08 | -0.085 | 0.89 | -0.59 | 94.91 | -5.09% | 15.02% | NO | 1.0 bps round trip |
| Route B Precision A+ | Route A/B | 1 | 0.12 | 0.00% | — | 1.09 | -1.089 | 0.00 | -1.09 | 94.56 | -5.44% | 5.44% | NO | 1.0 bps round trip |
| V3 M5 Trend Only | V3 M5 | 128 | 14.85 | 33.59% | 2.17 | 1.04 | 0.041 | 1.06 | 5.30 | 91.47 | -8.53% | 68.48% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | Structural A+ | 8 | 0.93 | 25.00% | 2.45 | 1.08 | -0.193 | 0.76 | -1.54 | 90.34 | -9.66% | 19.58% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | Structural A+ | 8 | 0.93 | 25.00% | 2.45 | 1.08 | -0.193 | 0.76 | -1.54 | 90.34 | -9.66% | 19.58% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | Structural A+ | 8 | 0.93 | 25.00% | 2.45 | 1.08 | -0.193 | 0.76 | -1.54 | 90.34 | -9.66% | 19.58% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB4 FULL_3_5R | Structural A+ | 8 | 0.93 | 25.00% | 2.39 | 1.08 | -0.209 | 0.74 | -1.67 | 89.82 | -10.18% | 19.58% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB6 FULL_3_5R | Structural A+ | 8 | 0.93 | 25.00% | 2.39 | 1.08 | -0.209 | 0.74 | -1.67 | 89.82 | -10.18% | 19.58% | NO | 1.0 bps round trip |
| Structural A+ R3.5 RB8 FULL_3_5R | Structural A+ | 8 | 0.93 | 25.00% | 2.39 | 1.08 | -0.209 | 0.74 | -1.67 | 89.82 | -10.18% | 19.58% | NO | 1.0 bps round trip |
| Outcome First RETEST_FVG | Outcome First | 2 | 0.23 | 0.00% | — | 1.05 | -1.053 | 0.00 | -2.11 | 89.75 | -10.25% | 10.25% | NO | 1.0 bps round trip |
| V3 Asymmetry pullback_only | V3 Asymmetry | 6 | 0.70 | 16.67% | 3.50 | 1.05 | -0.295 | 0.66 | -1.77 | 89.63 | -10.37% | 19.46% | NO | 1.0 bps round trip |
| Outcome First SWEEP_FVG_LONDON | Outcome First | 21 | 2.44 | 23.81% | 3.22 | 1.06 | -0.042 | 0.95 | -0.89 | 88.05 | -11.95% | 32.50% | NO | 1.0 bps round trip |
| V3 Asymmetry sweep_only | V3 Asymmetry | 8 | 0.93 | 12.50% | 4.96 | 1.05 | -0.300 | 0.67 | -2.40 | 85.52 | -14.48% | 19.22% | NO | 1.0 bps round trip |
| V3 Asymmetry quality_location | V3 Asymmetry | 3 | 0.35 | 0.00% | — | 1.06 | -1.063 | 0.00 | -3.19 | 84.89 | -15.11% | 15.11% | NO | 1.0 bps round trip |
| Structural Frequency DISPLACEMENT_RETRACE | Structural Frequency | 88 | 10.21 | 25.00% | 3.32 | 1.05 | 0.047 | 1.06 | 4.14 | 84.59 | -15.41% | 68.67% | NO | 1.0 bps round trip |
| Structural Frequency M15_LIQUIDITY_RETRACE | Structural Frequency | 88 | 10.21 | 25.00% | 3.32 | 1.05 | 0.047 | 1.06 | 4.14 | 84.58 | -15.42% | 68.67% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | Structural A+ | 10 | 1.16 | 20.00% | 2.45 | 1.07 | -0.361 | 0.58 | -3.61 | 81.25 | -18.75% | 26.02% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | Structural A+ | 10 | 1.16 | 20.00% | 2.45 | 1.07 | -0.361 | 0.58 | -3.61 | 81.25 | -18.75% | 26.02% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | Structural A+ | 10 | 1.16 | 20.00% | 2.45 | 1.07 | -0.361 | 0.58 | -3.61 | 81.25 | -18.75% | 26.02% | NO | 1.0 bps round trip |
| V3 Asymmetry balanced_3r | V3 Asymmetry | 13 | 1.51 | 15.38% | 4.23 | 1.05 | -0.242 | 0.73 | -3.15 | 80.79 | -19.21% | 27.50% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB4 FULL_3_5R | Structural A+ | 10 | 1.16 | 20.00% | 2.39 | 1.07 | -0.374 | 0.56 | -3.74 | 80.78 | -19.22% | 26.44% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB6 FULL_3_5R | Structural A+ | 10 | 1.16 | 20.00% | 2.39 | 1.07 | -0.374 | 0.56 | -3.74 | 80.78 | -19.22% | 26.44% | NO | 1.0 bps round trip |
| Structural A+ R3.0 RB8 FULL_3_5R | Structural A+ | 10 | 1.16 | 20.00% | 2.39 | 1.07 | -0.374 | 0.56 | -3.74 | 80.78 | -19.22% | 26.44% | NO | 1.0 bps round trip |
| V3 Asymmetry strict_4r | V3 Asymmetry | 4 | 0.46 | 0.00% | — | 1.06 | -1.058 | 0.00 | -4.23 | 80.45 | -19.55% | 19.55% | NO | 1.0 bps round trip |
| Outcome First PB_FVG | Outcome First | 9 | 1.04 | 11.11% | 3.42 | 1.06 | -0.564 | 0.40 | -5.07 | 75.69 | -24.31% | 27.65% | NO | 1.0 bps round trip |
| V3 Asymmetry high_frequency_quality | V3 Asymmetry | 29 | 3.36 | 20.69% | 3.32 | 1.06 | -0.150 | 0.82 | -4.35 | 72.01 | -27.99% | 45.24% | NO | 1.0 bps round trip |
| Structural Router QUALITY_CORE | Structural Router | 25 | 2.90 | 20.00% | 3.21 | 1.06 | -0.206 | 0.76 | -5.15 | 70.75 | -29.25% | 45.75% | NO | 1.0 bps round trip |
| Structural Router LONDON_CORE | Structural Router | 26 | 3.02 | 19.23% | 3.21 | 1.06 | -0.242 | 0.72 | -6.28 | 66.75 | -33.25% | 45.98% | NO | 1.0 bps round trip |
| V4 CORE | V4 Confluence | 343 | 39.80 | 55.98% | 0.48 | 1.00 | -0.013 | 0.93 | -4.30 | 66.40 | -33.60% | 58.65% | NO | no explicit transaction cost in v4 Python replay |
| A+ v2 ROBUST_EFF20 4.0R | V3 A+ v2 | 81 | 9.40 | 20.99% | 3.58 | 1.03 | -0.061 | 0.93 | -4.90 | 55.46 | -44.54% | 64.54% | NO | 1.0 bps round trip |
| A+ v2 ROBUST_EFF20 3.5R | V3 A+ v2 | 81 | 9.40 | 22.22% | 3.22 | 1.03 | -0.083 | 0.90 | -6.71 | 52.63 | -47.37% | 70.58% | NO | 1.0 bps round trip |
| V4 QUALITY65 London/NY proxy | V4 Confluence | 116 | 13.46 | 52.59% | 0.46 | 1.00 | -0.099 | 0.70 | -11.45 | 52.51 | -47.49% | 60.47% | NO | no explicit transaction cost in v4 Python replay |
| A+ v2 ADAPTIVE03 4.0R | V3 A+ v2 | 99 | 11.49 | 22.22% | 3.35 | 1.03 | -0.056 | 0.93 | -5.52 | 50.09 | -49.91% | 71.31% | NO | 1.0 bps round trip |
| V4 CORE SD SCORE65 | V4 Confluence | 174 | 20.19 | 55.17% | 0.41 | 1.00 | -0.077 | 0.73 | -13.35 | 46.52 | -53.48% | 61.33% | NO | no explicit transaction cost in v4 Python replay |
| A+ Hybrid HYBRID03 | V3 A+ Hybrid | 99 | 11.49 | 23.23% | 3.04 | 1.03 | -0.083 | 0.89 | -8.25 | 45.65 | -54.35% | 76.49% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE07 4.0R | V3 A+ v2 | 95 | 11.02 | 21.05% | 3.47 | 1.03 | -0.083 | 0.90 | -7.86 | 45.47 | -54.53% | 73.96% | NO | 1.0 bps round trip |
| V4 CORE SD M15 SCORE65 | V4 Confluence | 173 | 20.07 | 54.91% | 0.41 | 1.00 | -0.081 | 0.72 | -13.95 | 45.16 | -54.84% | 62.46% | NO | no explicit transaction cost in v4 Python replay |
| Outcome First PB_BODY | Outcome First | 19 | 2.20 | 5.26% | 3.45 | 1.04 | -0.807 | 0.18 | -15.33 | 44.70 | -55.30% | 55.30% | NO | 1.0 bps round trip |
| Outcome First PORTFOLIO_BODY | Outcome First | 42 | 4.87 | 16.67% | 3.28 | 1.05 | -0.329 | 0.62 | -13.83 | 43.70 | -56.30% | 66.40% | NO | 1.0 bps round trip |
| Structural Router ROBUST_CORE | Structural Router | 34 | 3.94 | 14.71% | 3.21 | 1.06 | -0.429 | 0.52 | -14.58 | 43.60 | -56.40% | 64.72% | NO | 1.0 bps round trip |
| Outcome First CORE_PB_SWEEP | Outcome First | 39 | 4.53 | 15.38% | 3.26 | 1.05 | -0.389 | 0.56 | -15.18 | 41.52 | -58.48% | 62.59% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE05 4.0R | V3 A+ v2 | 97 | 11.25 | 20.62% | 3.47 | 1.03 | -0.103 | 0.87 | -9.95 | 40.86 | -59.14% | 76.60% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE03 3.5R | V3 A+ v2 | 101 | 11.72 | 22.77% | 3.02 | 1.03 | -0.108 | 0.86 | -10.89 | 40.14 | -59.86% | 79.79% | NO | 1.0 bps round trip |
| A+ Hybrid HYBRID07 | V3 A+ Hybrid | 95 | 11.02 | 22.11% | 3.07 | 1.03 | -0.122 | 0.85 | -11.59 | 39.71 | -60.29% | 78.66% | NO | 1.0 bps round trip |
| A+ v2 ROBUST_EFF20 3.0R | V3 A+ v2 | 81 | 9.40 | 22.22% | 2.85 | 1.03 | -0.166 | 0.79 | -13.44 | 39.46 | -60.54% | 75.95% | NO | 1.0 bps round trip |
| V4 CORE SD SCORE60 | V4 Confluence | 225 | 26.11 | 51.11% | 0.45 | 1.00 | -0.076 | 0.73 | -17.10 | 37.38 | -62.62% | 70.64% | NO | no explicit transaction cost in v4 Python replay |
| Outcome First PORTFOLIO_FVG_RETEST | Outcome First | 41 | 4.76 | 14.63% | 3.26 | 1.05 | -0.422 | 0.53 | -17.28 | 37.26 | -62.74% | 66.43% | NO | 1.0 bps round trip |
| A+ Hybrid HYBRID05 | V3 A+ Hybrid | 97 | 11.25 | 21.65% | 3.12 | 1.03 | -0.131 | 0.84 | -12.67 | 37.24 | -62.76% | 80.82% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE07 3.5R | V3 A+ v2 | 97 | 11.25 | 21.65% | 3.12 | 1.03 | -0.131 | 0.84 | -12.73 | 37.21 | -62.79% | 81.26% | NO | 1.0 bps round trip |
| V4 CORE SD M15 SCORE60 | V4 Confluence | 224 | 25.99 | 50.89% | 0.45 | 1.00 | -0.079 | 0.72 | -17.70 | 36.29 | -63.71% | 71.50% | NO | no explicit transaction cost in v4 Python replay |
| A+ v2 ROBUST 3.5R | V3 A+ v2 | 93 | 10.79 | 20.43% | 3.23 | 1.03 | -0.159 | 0.81 | -14.74 | 34.21 | -65.79% | 80.87% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE03 3.0R | V3 A+ v2 | 101 | 11.72 | 23.76% | 2.67 | 1.03 | -0.150 | 0.81 | -15.12 | 34.17 | -65.83% | 84.18% | NO | 1.0 bps round trip |
| A+ Hybrid HYBRID10 | V3 A+ Hybrid | 92 | 10.67 | 21.74% | 2.93 | 1.03 | -0.168 | 0.79 | -15.46 | 33.88 | -66.12% | 78.20% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE05 3.5R | V3 A+ v2 | 99 | 11.49 | 21.21% | 3.12 | 1.03 | -0.150 | 0.82 | -14.82 | 33.44 | -66.56% | 83.16% | NO | 1.0 bps round trip |
| A+ v2 ROBUST 4.0R | V3 A+ v2 | 93 | 10.79 | 19.35% | 3.48 | 1.03 | -0.158 | 0.81 | -14.67 | 33.38 | -66.62% | 78.66% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE07 3.0R | V3 A+ v2 | 97 | 11.25 | 22.68% | 2.76 | 1.03 | -0.170 | 0.79 | -16.46 | 32.37 | -67.63% | 85.01% | NO | 1.0 bps round trip |
| A+ FREQUENCY SCALE_2R_RUN4R | V3 A+ v1 | 110 | 12.76 | 29.09% | 2.02 | 1.05 | -0.156 | 0.79 | -17.21 | 30.31 | -69.69% | 73.62% | NO | 1.0 bps round trip |
| V4 CORE SD M15 | V4 Confluence | 285 | 33.07 | 52.28% | 0.46 | 1.00 | -0.073 | 0.75 | -20.80 | 29.92 | -70.08% | 75.51% | NO | no explicit transaction cost in v4 Python replay |
| A+ v2 FREQ16 4.0R | V3 A+ v2 | 94 | 10.91 | 20.21% | 3.20 | 1.04 | -0.182 | 0.78 | -17.10 | 29.79 | -70.21% | 80.65% | NO | 1.0 bps round trip |
| A+ v2 ADAPTIVE05 3.0R | V3 A+ v2 | 99 | 11.49 | 22.22% | 2.76 | 1.03 | -0.187 | 0.77 | -18.55 | 29.08 | -70.92% | 86.53% | NO | 1.0 bps round trip |
| A+ APLUS_CORE SCALE_2R_RUN4R | V3 A+ v1 | 90 | 10.44 | 27.78% | 1.95 | 1.05 | -0.217 | 0.71 | -19.49 | 29.06 | -70.94% | 74.39% | NO | 1.0 bps round trip |
| A+ v2 FREQ16 3.5R | V3 A+ v2 | 96 | 11.14 | 20.83% | 2.95 | 1.04 | -0.208 | 0.75 | -19.92 | 26.65 | -73.35% | 84.25% | NO | 1.0 bps round trip |
| A+ v2 ROBUST 3.0R | V3 A+ v2 | 93 | 10.79 | 20.43% | 2.85 | 1.03 | -0.236 | 0.71 | -21.97 | 25.10 | -74.90% | 84.70% | NO | 1.0 bps round trip |
| A+ v2 FREQ16 3.0R | V3 A+ v2 | 96 | 11.14 | 21.88% | 2.63 | 1.04 | -0.236 | 0.71 | -22.65 | 24.20 | -75.80% | 87.13% | NO | 1.0 bps round trip |
| A+ APLUS_CORE FULL_3R | V3 A+ v1 | 90 | 10.44 | 20.00% | 2.77 | 1.04 | -0.279 | 0.67 | -25.11 | 21.87 | -78.13% | 83.43% | NO | 1.0 bps round trip |
| A+ FREQUENCY FULL_3R | V3 A+ v1 | 110 | 12.76 | 21.82% | 2.67 | 1.05 | -0.228 | 0.72 | -25.11 | 20.58 | -79.42% | 82.58% | NO | 1.0 bps round trip |

## Month-by-month

The full month-by-month matrix is saved as `monthly.csv`. Below are months with at least one trade.

| Strategy | Month | Trades | WR | Net R | P/L RM | Ending RM |
|---|---|---:|---:|---:|---:|---:|
| Legacy Python Regime Router | 2026-01 | 74 | 50.00% | 21.50 | 149.15 | 249.15 |
| Legacy Python Regime Router | 2026-02 | 78 | 30.77% | -18.00 | -160.57 | 88.58 |
| Legacy Python Regime Router | 2026-03 | 74 | 29.73% | -17.50 | -56.28 | 32.30 |
| Legacy Python Regime Router | 2026-04 | 100 | 45.00% | 15.50 | 24.71 | 57.02 |
| Legacy Python Regime Router | 2026-05 | 108 | 50.00% | 31.50 | 160.26 | 217.27 |
| Legacy Python Regime Router | 2026-06 | 112 | 38.39% | -0.00 | -44.15 | 173.13 |
| Legacy Python Regime Router | 2026-07 | 103 | 43.69% | 11.00 | 71.78 | 244.91 |
| Legacy Python Regime Router | 2026-08 | 90 | 40.00% | 3.00 | -7.57 | 237.34 |
| Legacy Python Regime Router | 2026-09 | 46 | 36.96% | -3.17 | -51.88 | 185.45 |
| V3 M5 Combined | 2026-01 | 16 | 37.50% | 2.68 | 9.07 | 109.07 |
| V3 M5 Combined | 2026-02 | 8 | 25.00% | -1.72 | -10.89 | 98.19 |
| V3 M5 Combined | 2026-03 | 21 | 38.10% | 4.09 | 15.08 | 113.27 |
| V3 M5 Combined | 2026-04 | 13 | 23.08% | -3.88 | -22.79 | 90.48 |
| V3 M5 Combined | 2026-05 | 13 | 38.46% | 2.58 | 8.57 | 99.05 |
| V3 M5 Combined | 2026-06 | 21 | 19.05% | -8.94 | -38.54 | 60.51 |
| V3 M5 Combined | 2026-07 | 12 | 33.33% | 1.06 | 0.95 | 61.46 |
| V3 M5 Combined | 2026-08 | 17 | 52.94% | 11.96 | 43.29 | 104.75 |
| V3 M5 Combined | 2026-09 | 10 | 40.00% | 2.43 | 10.02 | 114.77 |
| V3 Classic M15 Only | 2026-02 | 1 | 0.00% | -1.01 | -5.04 | 94.96 |
| V3 Classic M15 Only | 2026-06 | 1 | 0.00% | -1.02 | -4.84 | 90.12 |
| V3 Classic M15 Only | 2026-07 | 1 | 100.00% | 2.95 | 13.29 | 103.41 |
| V3 Classic M15 Only | 2026-08 | 1 | 100.00% | 2.97 | 15.38 | 118.79 |
| V3 M5 Trend Only | 2026-01 | 16 | 37.50% | 2.68 | 9.07 | 109.07 |
| V3 M5 Trend Only | 2026-02 | 7 | 28.57% | -0.71 | -5.67 | 103.40 |
| V3 M5 Trend Only | 2026-03 | 21 | 38.10% | 4.09 | 15.88 | 119.28 |
| V3 M5 Trend Only | 2026-04 | 13 | 23.08% | -3.88 | -24.00 | 95.28 |
| V3 M5 Trend Only | 2026-05 | 13 | 38.46% | 2.58 | 9.03 | 104.31 |
| V3 M5 Trend Only | 2026-06 | 20 | 20.00% | -7.92 | -37.17 | 67.14 |
| V3 M5 Trend Only | 2026-07 | 11 | 27.27% | -1.89 | -7.71 | 59.43 |
| V3 M5 Trend Only | 2026-08 | 17 | 47.06% | 7.92 | 24.06 | 83.49 |
| V3 M5 Trend Only | 2026-09 | 10 | 40.00% | 2.43 | 7.99 | 91.47 |
| V3 Asymmetry balanced_3r | 2026-01 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| V3 Asymmetry balanced_3r | 2026-03 | 1 | 0.00% | -1.02 | -4.85 | 90.03 |
| V3 Asymmetry balanced_3r | 2026-04 | 1 | 0.00% | -1.06 | -4.76 | 85.27 |
| V3 Asymmetry balanced_3r | 2026-05 | 1 | 0.00% | -1.06 | -4.52 | 80.74 |
| V3 Asymmetry balanced_3r | 2026-06 | 3 | 33.33% | 2.86 | 9.73 | 90.47 |
| V3 Asymmetry balanced_3r | 2026-07 | 3 | 0.00% | -3.20 | -13.72 | 76.76 |
| V3 Asymmetry balanced_3r | 2026-08 | 1 | 0.00% | -1.08 | -4.16 | 72.60 |
| V3 Asymmetry balanced_3r | 2026-09 | 2 | 50.00% | 2.44 | 8.19 | 80.79 |
| V3 Asymmetry balanced_3_5r | 2026-03 | 1 | 0.00% | -1.02 | -5.11 | 94.89 |
| V3 Asymmetry balanced_3_5r | 2026-04 | 1 | 0.00% | -1.06 | -5.02 | 89.87 |
| V3 Asymmetry balanced_3_5r | 2026-05 | 1 | 0.00% | -1.06 | -4.77 | 85.10 |
| V3 Asymmetry balanced_3_5r | 2026-06 | 3 | 33.33% | 2.99 | 10.74 | 95.84 |
| V3 Asymmetry balanced_3_5r | 2026-07 | 2 | 0.00% | -2.15 | -10.02 | 85.82 |
| V3 Asymmetry balanced_3_5r | 2026-08 | 1 | 0.00% | -1.08 | -4.65 | 81.17 |
| V3 Asymmetry balanced_3_5r | 2026-09 | 1 | 100.00% | 3.50 | 14.19 | 95.36 |
| V3 Asymmetry strict_4r | 2026-03 | 1 | 0.00% | -1.02 | -5.11 | 94.89 |
| V3 Asymmetry strict_4r | 2026-04 | 1 | 0.00% | -1.06 | -5.02 | 89.87 |
| V3 Asymmetry strict_4r | 2026-07 | 1 | 0.00% | -1.07 | -4.80 | 85.06 |
| V3 Asymmetry strict_4r | 2026-08 | 1 | 0.00% | -1.08 | -4.61 | 80.45 |
| V3 Asymmetry quality_location | 2026-04 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| V3 Asymmetry quality_location | 2026-06 | 1 | 0.00% | -1.05 | -4.96 | 89.75 |
| V3 Asymmetry quality_location | 2026-08 | 1 | 0.00% | -1.08 | -4.86 | 84.89 |
| V3 Asymmetry pullback_only | 2026-01 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| V3 Asymmetry pullback_only | 2026-04 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| V3 Asymmetry pullback_only | 2026-06 | 1 | 0.00% | -1.05 | -4.71 | 85.15 |
| V3 Asymmetry pullback_only | 2026-08 | 1 | 0.00% | -1.08 | -4.61 | 80.54 |
| V3 Asymmetry pullback_only | 2026-09 | 2 | 50.00% | 2.44 | 9.09 | 89.63 |
| V3 Asymmetry sweep_only | 2026-01 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| V3 Asymmetry sweep_only | 2026-03 | 1 | 0.00% | -1.02 | -4.85 | 90.03 |
| V3 Asymmetry sweep_only | 2026-05 | 1 | 0.00% | -1.06 | -4.78 | 85.25 |
| V3 Asymmetry sweep_only | 2026-06 | 2 | 50.00% | 3.91 | 15.55 | 100.81 |
| V3 Asymmetry sweep_only | 2026-07 | 3 | 0.00% | -3.20 | -15.28 | 85.52 |
| V3 Asymmetry high_frequency_quality | 2026-01 | 2 | 50.00% | 1.80 | 8.30 | 108.30 |
| V3 Asymmetry high_frequency_quality | 2026-02 | 1 | 0.00% | -1.02 | -5.50 | 102.80 |
| V3 Asymmetry high_frequency_quality | 2026-03 | 2 | 50.00% | 2.18 | 10.38 | 113.18 |
| V3 Asymmetry high_frequency_quality | 2026-04 | 3 | 0.00% | -3.18 | -17.05 | 96.12 |
| V3 Asymmetry high_frequency_quality | 2026-05 | 3 | 33.33% | 0.80 | 2.68 | 98.81 |
| V3 Asymmetry high_frequency_quality | 2026-06 | 4 | 50.00% | 5.63 | 27.24 | 126.05 |
| V3 Asymmetry high_frequency_quality | 2026-07 | 6 | 0.00% | -6.42 | -35.41 | 90.64 |
| V3 Asymmetry high_frequency_quality | 2026-08 | 3 | 0.00% | -3.18 | -13.66 | 76.98 |
| V3 Asymmetry high_frequency_quality | 2026-09 | 5 | 20.00% | -0.98 | -4.96 | 72.01 |
| A+ APLUS_CORE FULL_3R | 2026-01 | 12 | 16.67% | -5.84 | -27.10 | 72.90 |
| A+ APLUS_CORE FULL_3R | 2026-02 | 14 | 28.57% | 0.04 | -3.22 | 69.68 |
| A+ APLUS_CORE FULL_3R | 2026-03 | 7 | 14.29% | -3.24 | -11.49 | 58.19 |
| A+ APLUS_CORE FULL_3R | 2026-04 | 9 | 22.22% | -1.31 | -5.27 | 52.92 |
| A+ APLUS_CORE FULL_3R | 2026-05 | 7 | 28.57% | 0.65 | 0.31 | 53.22 |
| A+ APLUS_CORE FULL_3R | 2026-06 | 11 | 27.27% | 0.40 | -1.14 | 52.09 |
| A+ APLUS_CORE FULL_3R | 2026-07 | 10 | 10.00% | -6.65 | -15.59 | 36.50 |
| A+ APLUS_CORE FULL_3R | 2026-08 | 11 | 0.00% | -11.63 | -16.42 | 20.08 |
| A+ APLUS_CORE FULL_3R | 2026-09 | 9 | 33.33% | 2.47 | 1.79 | 21.87 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-01 | 12 | 25.00% | -4.49 | -22.33 | 77.67 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-02 | 14 | 28.57% | 0.10 | -3.38 | 74.29 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-03 | 7 | 14.29% | -2.64 | -10.63 | 63.67 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-04 | 9 | 22.22% | -1.89 | -7.33 | 56.34 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-05 | 7 | 28.57% | 1.85 | 3.33 | 59.67 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-06 | 11 | 54.55% | 6.40 | 18.47 | 78.14 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-07 | 10 | 30.00% | -6.45 | -22.14 | 56.00 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-08 | 11 | 9.09% | -10.23 | -22.92 | 33.08 |
| A+ APLUS_CORE SCALE_2R_RUN4R | 2026-09 | 9 | 33.33% | -2.13 | -4.02 | 29.06 |
| A+ FREQUENCY FULL_3R | 2026-01 | 15 | 26.67% | -2.23 | -14.38 | 85.62 |
| A+ FREQUENCY FULL_3R | 2026-02 | 18 | 16.67% | -8.10 | -30.98 | 54.64 |
| A+ FREQUENCY FULL_3R | 2026-03 | 7 | 28.57% | 0.72 | 0.49 | 55.14 |
| A+ FREQUENCY FULL_3R | 2026-04 | 10 | 30.00% | -0.22 | -2.28 | 52.86 |
| A+ FREQUENCY FULL_3R | 2026-05 | 16 | 18.75% | -3.65 | -10.83 | 42.03 |
| A+ FREQUENCY FULL_3R | 2026-06 | 12 | 25.00% | -0.63 | -3.01 | 39.02 |
| A+ FREQUENCY FULL_3R | 2026-07 | 15 | 20.00% | -5.11 | -9.99 | 29.02 |
| A+ FREQUENCY FULL_3R | 2026-08 | 13 | 7.69% | -9.67 | -11.61 | 17.42 |
| A+ FREQUENCY FULL_3R | 2026-09 | 4 | 50.00% | 3.78 | 3.16 | 20.58 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-01 | 15 | 33.33% | 0.30 | -3.48 | 96.52 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-02 | 18 | 16.67% | -8.64 | -36.45 | 60.07 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-03 | 7 | 42.86% | 3.32 | 8.46 | 68.53 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-04 | 10 | 30.00% | -1.35 | -6.30 | 62.23 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-05 | 16 | 25.00% | -4.67 | -15.15 | 47.08 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-06 | 12 | 41.67% | 3.97 | 7.39 | 54.47 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-07 | 15 | 33.33% | -4.25 | -11.82 | 42.65 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-08 | 13 | 15.38% | -7.67 | -14.44 | 28.20 |
| A+ FREQUENCY SCALE_2R_RUN4R | 2026-09 | 4 | 50.00% | 1.78 | 2.11 | 30.31 |
| A+ v2 ROBUST 3.0R | 2026-01 | 12 | 8.33% | -9.84 | -39.84 | 60.16 |
| A+ v2 ROBUST 3.0R | 2026-02 | 13 | 15.38% | -5.57 | -16.24 | 43.93 |
| A+ v2 ROBUST 3.0R | 2026-03 | 8 | 25.00% | -0.28 | -1.81 | 42.12 |
| A+ v2 ROBUST 3.0R | 2026-04 | 13 | 15.38% | -5.52 | -11.27 | 30.85 |
| A+ v2 ROBUST 3.0R | 2026-05 | 9 | 33.33% | 3.46 | 4.48 | 35.32 |
| A+ v2 ROBUST 3.0R | 2026-06 | 10 | 30.00% | 1.44 | 1.15 | 36.48 |
| A+ v2 ROBUST 3.0R | 2026-07 | 10 | 10.00% | -6.63 | -10.88 | 25.59 |
| A+ v2 ROBUST 3.0R | 2026-08 | 12 | 8.33% | -8.66 | -9.41 | 16.18 |
| A+ v2 ROBUST 3.0R | 2026-09 | 6 | 66.67% | 9.63 | 8.92 | 25.10 |
| A+ v2 ROBUST 3.5R | 2026-01 | 12 | 8.33% | -9.84 | -39.84 | 60.16 |
| A+ v2 ROBUST 3.5R | 2026-02 | 13 | 15.38% | -6.34 | -17.76 | 42.40 |
| A+ v2 ROBUST 3.5R | 2026-03 | 8 | 25.00% | 0.72 | 0.04 | 42.45 |
| A+ v2 ROBUST 3.5R | 2026-04 | 13 | 15.38% | -4.52 | -9.99 | 32.46 |
| A+ v2 ROBUST 3.5R | 2026-05 | 9 | 33.33% | 4.96 | 7.19 | 39.65 |
| A+ v2 ROBUST 3.5R | 2026-06 | 10 | 30.00% | 2.94 | 4.03 | 43.68 |
| A+ v2 ROBUST 3.5R | 2026-07 | 10 | 10.00% | -6.13 | -12.36 | 31.31 |
| A+ v2 ROBUST 3.5R | 2026-08 | 12 | 8.33% | -8.16 | -11.09 | 20.23 |
| A+ v2 ROBUST 3.5R | 2026-09 | 6 | 66.67% | 11.63 | 13.98 | 34.21 |
| A+ v2 ROBUST 4.0R | 2026-01 | 12 | 8.33% | -9.84 | -39.84 | 60.16 |
| A+ v2 ROBUST 4.0R | 2026-02 | 13 | 15.38% | -5.84 | -16.86 | 43.30 |
| A+ v2 ROBUST 4.0R | 2026-03 | 8 | 25.00% | 1.72 | 1.91 | 45.22 |
| A+ v2 ROBUST 4.0R | 2026-04 | 13 | 15.38% | -5.75 | -12.52 | 32.70 |
| A+ v2 ROBUST 4.0R | 2026-05 | 9 | 33.33% | 5.27 | 7.75 | 40.45 |
| A+ v2 ROBUST 4.0R | 2026-06 | 10 | 30.00% | 4.44 | 7.02 | 47.47 |
| A+ v2 ROBUST 4.0R | 2026-07 | 10 | 10.00% | -5.63 | -12.71 | 34.76 |
| A+ v2 ROBUST 4.0R | 2026-08 | 12 | 8.33% | -7.66 | -11.83 | 22.93 |
| A+ v2 ROBUST 4.0R | 2026-09 | 6 | 50.00% | 8.63 | 10.45 | 33.38 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-01 | 11 | 9.09% | -8.79 | -36.50 | 63.50 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-02 | 10 | 10.00% | -6.42 | -18.49 | 45.02 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-03 | 7 | 28.57% | 0.74 | 0.47 | 45.49 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-04 | 10 | 20.00% | -2.45 | -6.49 | 39.00 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-05 | 8 | 37.50% | 4.49 | 8.11 | 47.10 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-06 | 9 | 33.33% | 2.51 | 4.28 | 51.38 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-07 | 9 | 11.11% | -5.55 | -13.28 | 38.10 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-08 | 11 | 9.09% | -7.60 | -12.67 | 25.43 |
| A+ v2 ROBUST_EFF20 3.0R | 2026-09 | 6 | 66.67% | 9.63 | 14.03 | 39.46 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-01 | 11 | 9.09% | -8.79 | -36.50 | 63.50 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-02 | 10 | 10.00% | -7.69 | -20.97 | 42.53 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-03 | 7 | 28.57% | 1.74 | 2.34 | 44.87 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-04 | 10 | 20.00% | -1.45 | -4.71 | 40.16 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-05 | 8 | 37.50% | 5.99 | 11.59 | 51.75 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-06 | 9 | 33.33% | 4.01 | 8.47 | 60.22 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-07 | 9 | 11.11% | -5.05 | -14.60 | 45.62 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-08 | 11 | 9.09% | -7.10 | -14.50 | 31.12 |
| A+ v2 ROBUST_EFF20 3.5R | 2026-09 | 6 | 66.67% | 11.63 | 21.51 | 52.63 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-01 | 11 | 9.09% | -8.79 | -36.50 | 63.50 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-02 | 10 | 10.00% | -7.69 | -20.97 | 42.53 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-03 | 7 | 28.57% | 2.74 | 4.27 | 46.80 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-04 | 10 | 20.00% | -0.45 | -3.10 | 43.70 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-05 | 8 | 37.50% | 6.30 | 13.31 | 57.01 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-06 | 9 | 33.33% | 5.51 | 13.67 | 70.67 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-07 | 9 | 11.11% | -4.55 | -15.99 | 54.69 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-08 | 11 | 9.09% | -6.60 | -16.59 | 38.10 |
| A+ v2 ROBUST_EFF20 4.0R | 2026-09 | 6 | 50.00% | 8.63 | 17.36 | 55.46 |
| A+ v2 FREQ16 3.0R | 2026-01 | 13 | 7.69% | -10.87 | -42.93 | 57.07 |
| A+ v2 FREQ16 3.0R | 2026-02 | 10 | 20.00% | -2.43 | -8.10 | 48.97 |
| A+ v2 FREQ16 3.0R | 2026-03 | 7 | 28.57% | 0.77 | 0.57 | 49.54 |
| A+ v2 FREQ16 3.0R | 2026-04 | 11 | 18.18% | -3.38 | -9.03 | 40.51 |
| A+ v2 FREQ16 3.0R | 2026-05 | 8 | 25.00% | -0.36 | -1.83 | 38.68 |
| A+ v2 FREQ16 3.0R | 2026-06 | 14 | 28.57% | -1.18 | -3.79 | 34.89 |
| A+ v2 FREQ16 3.0R | 2026-07 | 10 | 10.00% | -6.61 | -10.39 | 24.50 |
| A+ v2 FREQ16 3.0R | 2026-08 | 14 | 14.29% | -9.07 | -9.35 | 15.14 |
| A+ v2 FREQ16 3.0R | 2026-09 | 9 | 55.56% | 10.48 | 9.06 | 24.20 |
| A+ v2 FREQ16 3.5R | 2026-01 | 13 | 7.69% | -10.87 | -42.93 | 57.07 |
| A+ v2 FREQ16 3.5R | 2026-02 | 10 | 20.00% | -3.20 | -9.80 | 47.27 |
| A+ v2 FREQ16 3.5R | 2026-03 | 7 | 28.57% | 1.77 | 2.66 | 49.93 |
| A+ v2 FREQ16 3.5R | 2026-04 | 11 | 18.18% | -2.38 | -7.31 | 42.62 |
| A+ v2 FREQ16 3.5R | 2026-05 | 8 | 25.00% | 0.64 | -0.13 | 42.49 |
| A+ v2 FREQ16 3.5R | 2026-06 | 14 | 28.57% | 0.32 | -1.61 | 40.88 |
| A+ v2 FREQ16 3.5R | 2026-07 | 10 | 10.00% | -6.11 | -11.55 | 29.33 |
| A+ v2 FREQ16 3.5R | 2026-08 | 14 | 14.29% | -8.57 | -10.80 | 18.53 |
| A+ v2 FREQ16 3.5R | 2026-09 | 9 | 44.44% | 8.48 | 8.13 | 26.65 |
| A+ v2 FREQ16 4.0R | 2026-01 | 13 | 7.69% | -10.87 | -42.93 | 57.07 |
| A+ v2 FREQ16 4.0R | 2026-02 | 10 | 20.00% | -2.70 | -8.80 | 48.27 |
| A+ v2 FREQ16 4.0R | 2026-03 | 7 | 28.57% | 2.77 | 4.91 | 53.19 |
| A+ v2 FREQ16 4.0R | 2026-04 | 11 | 18.18% | -3.61 | -10.24 | 42.94 |
| A+ v2 FREQ16 4.0R | 2026-05 | 8 | 25.00% | 1.64 | 1.71 | 44.66 |
| A+ v2 FREQ16 4.0R | 2026-06 | 12 | 33.33% | 3.88 | 6.22 | 50.88 |
| A+ v2 FREQ16 4.0R | 2026-07 | 10 | 10.00% | -5.61 | -13.60 | 37.29 |
| A+ v2 FREQ16 4.0R | 2026-08 | 14 | 14.29% | -8.07 | -13.23 | 24.05 |
| A+ v2 FREQ16 4.0R | 2026-09 | 9 | 33.33% | 5.48 | 5.73 | 29.79 |
| A+ v2 ADAPTIVE03 3.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE03 3.0R | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ v2 ADAPTIVE03 3.0R | 2026-03 | 8 | 37.50% | 3.72 | 6.87 | 49.51 |
| A+ v2 ADAPTIVE03 3.0R | 2026-04 | 12 | 16.67% | -4.52 | -11.34 | 38.17 |
| A+ v2 ADAPTIVE03 3.0R | 2026-05 | 11 | 27.27% | 1.38 | 1.13 | 39.30 |
| A+ v2 ADAPTIVE03 3.0R | 2026-06 | 13 | 30.77% | -0.11 | -1.86 | 37.44 |
| A+ v2 ADAPTIVE03 3.0R | 2026-07 | 10 | 10.00% | -6.60 | -11.13 | 26.31 |
| A+ v2 ADAPTIVE03 3.0R | 2026-08 | 16 | 18.75% | -7.22 | -8.67 | 17.64 |
| A+ v2 ADAPTIVE03 3.0R | 2026-09 | 9 | 66.67% | 14.49 | 16.52 | 34.17 |
| A+ v2 ADAPTIVE03 3.5R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE03 3.5R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE03 3.5R | 2026-03 | 8 | 37.50% | 5.22 | 9.61 | 49.90 |
| A+ v2 ADAPTIVE03 3.5R | 2026-04 | 12 | 16.67% | -3.52 | -9.74 | 40.16 |
| A+ v2 ADAPTIVE03 3.5R | 2026-05 | 11 | 27.27% | 2.88 | 3.95 | 44.11 |
| A+ v2 ADAPTIVE03 3.5R | 2026-06 | 13 | 30.77% | 1.39 | 0.72 | 44.83 |
| A+ v2 ADAPTIVE03 3.5R | 2026-07 | 10 | 10.00% | -6.10 | -12.64 | 32.19 |
| A+ v2 ADAPTIVE03 3.5R | 2026-08 | 16 | 18.75% | -6.22 | -9.66 | 22.54 |
| A+ v2 ADAPTIVE03 3.5R | 2026-09 | 9 | 55.56% | 12.99 | 17.60 | 40.14 |
| A+ v2 ADAPTIVE03 4.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE03 4.0R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE03 4.0R | 2026-03 | 8 | 37.50% | 6.72 | 12.87 | 53.16 |
| A+ v2 ADAPTIVE03 4.0R | 2026-04 | 12 | 16.67% | -2.52 | -8.53 | 44.63 |
| A+ v2 ADAPTIVE03 4.0R | 2026-05 | 11 | 27.27% | 3.19 | 5.00 | 49.63 |
| A+ v2 ADAPTIVE03 4.0R | 2026-06 | 11 | 36.36% | 4.95 | 10.10 | 59.73 |
| A+ v2 ADAPTIVE03 4.0R | 2026-07 | 10 | 10.00% | -5.60 | -15.92 | 43.81 |
| A+ v2 ADAPTIVE03 4.0R | 2026-08 | 16 | 18.75% | -5.22 | -11.82 | 31.99 |
| A+ v2 ADAPTIVE03 4.0R | 2026-09 | 9 | 44.44% | 10.49 | 18.09 | 50.09 |
| A+ v2 ADAPTIVE05 3.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE05 3.0R | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ v2 ADAPTIVE05 3.0R | 2026-03 | 8 | 37.50% | 3.72 | 6.87 | 49.51 |
| A+ v2 ADAPTIVE05 3.0R | 2026-04 | 12 | 16.67% | -4.52 | -11.34 | 38.17 |
| A+ v2 ADAPTIVE05 3.0R | 2026-05 | 11 | 27.27% | 1.38 | 1.13 | 39.30 |
| A+ v2 ADAPTIVE05 3.0R | 2026-06 | 13 | 23.08% | -1.63 | -4.64 | 34.66 |
| A+ v2 ADAPTIVE05 3.0R | 2026-07 | 10 | 10.00% | -6.60 | -10.30 | 24.36 |
| A+ v2 ADAPTIVE05 3.0R | 2026-08 | 14 | 14.29% | -9.12 | -9.34 | 15.02 |
| A+ v2 ADAPTIVE05 3.0R | 2026-09 | 9 | 66.67% | 14.49 | 14.07 | 29.08 |
| A+ v2 ADAPTIVE05 3.5R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE05 3.5R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE05 3.5R | 2026-03 | 8 | 37.50% | 5.22 | 9.61 | 49.90 |
| A+ v2 ADAPTIVE05 3.5R | 2026-04 | 12 | 16.67% | -3.52 | -9.74 | 40.16 |
| A+ v2 ADAPTIVE05 3.5R | 2026-05 | 11 | 27.27% | 2.88 | 3.95 | 44.11 |
| A+ v2 ADAPTIVE05 3.5R | 2026-06 | 13 | 23.08% | -0.13 | -2.61 | 41.50 |
| A+ v2 ADAPTIVE05 3.5R | 2026-07 | 10 | 10.00% | -6.10 | -11.70 | 29.80 |
| A+ v2 ADAPTIVE05 3.5R | 2026-08 | 14 | 14.29% | -8.62 | -11.03 | 18.78 |
| A+ v2 ADAPTIVE05 3.5R | 2026-09 | 9 | 55.56% | 12.99 | 14.66 | 33.44 |
| A+ v2 ADAPTIVE05 4.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE05 4.0R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE05 4.0R | 2026-03 | 8 | 37.50% | 6.72 | 12.87 | 53.16 |
| A+ v2 ADAPTIVE05 4.0R | 2026-04 | 12 | 16.67% | -2.52 | -8.53 | 44.63 |
| A+ v2 ADAPTIVE05 4.0R | 2026-05 | 11 | 27.27% | 3.19 | 5.00 | 49.63 |
| A+ v2 ADAPTIVE05 4.0R | 2026-06 | 11 | 27.27% | 3.43 | 5.66 | 55.29 |
| A+ v2 ADAPTIVE05 4.0R | 2026-07 | 10 | 10.00% | -5.60 | -14.74 | 40.55 |
| A+ v2 ADAPTIVE05 4.0R | 2026-08 | 14 | 14.29% | -8.12 | -14.46 | 26.10 |
| A+ v2 ADAPTIVE05 4.0R | 2026-09 | 9 | 44.44% | 10.49 | 14.76 | 40.86 |
| A+ v2 ADAPTIVE07 3.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE07 3.0R | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ v2 ADAPTIVE07 3.0R | 2026-03 | 8 | 37.50% | 3.72 | 6.87 | 49.51 |
| A+ v2 ADAPTIVE07 3.0R | 2026-04 | 11 | 18.18% | -3.48 | -9.25 | 40.26 |
| A+ v2 ADAPTIVE07 3.0R | 2026-05 | 10 | 30.00% | 2.43 | 3.47 | 43.73 |
| A+ v2 ADAPTIVE07 3.0R | 2026-06 | 13 | 23.08% | -1.63 | -5.16 | 38.57 |
| A+ v2 ADAPTIVE07 3.0R | 2026-07 | 10 | 10.00% | -6.60 | -11.46 | 27.11 |
| A+ v2 ADAPTIVE07 3.0R | 2026-08 | 14 | 14.29% | -9.12 | -10.39 | 16.71 |
| A+ v2 ADAPTIVE07 3.0R | 2026-09 | 9 | 66.67% | 14.49 | 15.65 | 32.37 |
| A+ v2 ADAPTIVE07 3.5R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE07 3.5R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE07 3.5R | 2026-03 | 8 | 37.50% | 5.22 | 9.61 | 49.90 |
| A+ v2 ADAPTIVE07 3.5R | 2026-04 | 11 | 18.18% | -2.48 | -7.54 | 42.36 |
| A+ v2 ADAPTIVE07 3.5R | 2026-05 | 10 | 30.00% | 3.93 | 6.72 | 49.09 |
| A+ v2 ADAPTIVE07 3.5R | 2026-06 | 13 | 23.08% | -0.13 | -2.90 | 46.18 |
| A+ v2 ADAPTIVE07 3.5R | 2026-07 | 10 | 10.00% | -6.10 | -13.02 | 33.16 |
| A+ v2 ADAPTIVE07 3.5R | 2026-08 | 14 | 14.29% | -8.62 | -12.27 | 20.90 |
| A+ v2 ADAPTIVE07 3.5R | 2026-09 | 9 | 55.56% | 12.99 | 16.32 | 37.21 |
| A+ v2 ADAPTIVE07 4.0R | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ v2 ADAPTIVE07 4.0R | 2026-02 | 10 | 10.00% | -7.69 | -19.87 | 40.29 |
| A+ v2 ADAPTIVE07 4.0R | 2026-03 | 8 | 37.50% | 6.72 | 12.87 | 53.16 |
| A+ v2 ADAPTIVE07 4.0R | 2026-04 | 11 | 18.18% | -1.48 | -6.09 | 47.07 |
| A+ v2 ADAPTIVE07 4.0R | 2026-05 | 10 | 30.00% | 4.24 | 8.16 | 55.23 |
| A+ v2 ADAPTIVE07 4.0R | 2026-06 | 11 | 27.27% | 3.43 | 6.30 | 61.53 |
| A+ v2 ADAPTIVE07 4.0R | 2026-07 | 10 | 10.00% | -5.60 | -16.40 | 45.13 |
| A+ v2 ADAPTIVE07 4.0R | 2026-08 | 14 | 14.29% | -8.12 | -16.09 | 29.04 |
| A+ v2 ADAPTIVE07 4.0R | 2026-09 | 9 | 44.44% | 10.49 | 16.43 | 45.47 |
| A+ Hybrid HYBRID03 | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ Hybrid HYBRID03 | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ Hybrid HYBRID03 | 2026-03 | 8 | 37.50% | 5.72 | 11.28 | 53.92 |
| A+ Hybrid HYBRID03 | 2026-04 | 12 | 16.67% | -3.52 | -10.54 | 43.38 |
| A+ Hybrid HYBRID03 | 2026-05 | 11 | 27.27% | 2.19 | 2.85 | 46.22 |
| A+ Hybrid HYBRID03 | 2026-06 | 11 | 36.36% | 3.95 | 7.09 | 53.31 |
| A+ Hybrid HYBRID03 | 2026-07 | 10 | 10.00% | -6.60 | -15.84 | 37.47 |
| A+ Hybrid HYBRID03 | 2026-08 | 16 | 18.75% | -6.22 | -11.25 | 26.22 |
| A+ Hybrid HYBRID03 | 2026-09 | 9 | 55.56% | 12.49 | 19.44 | 45.65 |
| A+ Hybrid HYBRID05 | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ Hybrid HYBRID05 | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ Hybrid HYBRID05 | 2026-03 | 8 | 37.50% | 5.72 | 11.28 | 53.92 |
| A+ Hybrid HYBRID05 | 2026-04 | 12 | 16.67% | -3.52 | -10.54 | 43.38 |
| A+ Hybrid HYBRID05 | 2026-05 | 11 | 27.27% | 2.19 | 2.85 | 46.22 |
| A+ Hybrid HYBRID05 | 2026-06 | 11 | 27.27% | 2.43 | 3.12 | 49.35 |
| A+ Hybrid HYBRID05 | 2026-07 | 10 | 10.00% | -6.60 | -14.67 | 34.68 |
| A+ Hybrid HYBRID05 | 2026-08 | 14 | 14.29% | -9.12 | -13.30 | 21.38 |
| A+ Hybrid HYBRID05 | 2026-09 | 9 | 55.56% | 12.49 | 15.85 | 37.24 |
| A+ Hybrid HYBRID07 | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ Hybrid HYBRID07 | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ Hybrid HYBRID07 | 2026-03 | 8 | 37.50% | 5.72 | 11.28 | 53.92 |
| A+ Hybrid HYBRID07 | 2026-04 | 11 | 18.18% | -2.48 | -8.17 | 45.75 |
| A+ Hybrid HYBRID07 | 2026-05 | 10 | 30.00% | 3.24 | 5.69 | 51.44 |
| A+ Hybrid HYBRID07 | 2026-06 | 11 | 27.27% | 2.43 | 3.48 | 54.92 |
| A+ Hybrid HYBRID07 | 2026-07 | 10 | 10.00% | -6.60 | -16.32 | 38.60 |
| A+ Hybrid HYBRID07 | 2026-08 | 14 | 14.29% | -9.12 | -14.80 | 23.80 |
| A+ Hybrid HYBRID07 | 2026-09 | 9 | 55.56% | 11.49 | 15.91 | 39.71 |
| A+ Hybrid HYBRID10 | 2026-01 | 12 | 8.33% | -9.85 | -39.84 | 60.16 |
| A+ Hybrid HYBRID10 | 2026-02 | 10 | 10.00% | -6.42 | -17.51 | 42.65 |
| A+ Hybrid HYBRID10 | 2026-03 | 8 | 37.50% | 5.72 | 11.28 | 53.92 |
| A+ Hybrid HYBRID10 | 2026-04 | 10 | 20.00% | -2.45 | -7.69 | 46.23 |
| A+ Hybrid HYBRID10 | 2026-05 | 10 | 30.00% | 2.24 | 3.57 | 49.80 |
| A+ Hybrid HYBRID10 | 2026-06 | 11 | 27.27% | 2.43 | 3.37 | 53.17 |
| A+ Hybrid HYBRID10 | 2026-07 | 9 | 11.11% | -5.55 | -13.75 | 39.42 |
| A+ Hybrid HYBRID10 | 2026-08 | 14 | 14.29% | -9.12 | -15.11 | 24.31 |
| A+ Hybrid HYBRID10 | 2026-09 | 8 | 50.00% | 7.55 | 9.57 | 33.88 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-04 | 2 | 50.00% | 0.43 | 1.61 | 91.47 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -4.87 | 86.60 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -8.93 | 77.67 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.11 | 73.56 |
| Structural A+ R3.0 RB4 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 7.22 | 80.78 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-04 | 2 | 50.00% | 0.56 | 2.14 | 92.00 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -4.90 | 87.10 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -8.98 | 78.12 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.14 | 73.98 |
| Structural A+ R3.0 RB4 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 7.26 | 81.25 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-04 | 2 | 50.00% | 0.43 | 1.61 | 91.47 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -4.87 | 86.60 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -8.93 | 77.67 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.11 | 73.56 |
| Structural A+ R3.0 RB6 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 7.22 | 80.78 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-04 | 2 | 50.00% | 0.56 | 2.14 | 92.00 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -4.90 | 87.10 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -8.98 | 78.12 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.14 | 73.98 |
| Structural A+ R3.0 RB6 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 7.26 | 81.25 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-04 | 2 | 50.00% | 0.43 | 1.61 | 91.47 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -4.87 | 86.60 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -8.93 | 77.67 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.11 | 73.56 |
| Structural A+ R3.0 RB8 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 7.22 | 80.78 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-02 | 1 | 0.00% | -1.02 | -5.12 | 94.88 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.02 | 89.86 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-04 | 2 | 50.00% | 0.56 | 2.14 | 92.00 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -4.90 | 87.10 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -8.98 | 78.12 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.14 | 73.98 |
| Structural A+ R3.0 RB8 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 7.26 | 81.25 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -9.93 | 86.36 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.57 | 81.79 |
| Structural A+ R3.5 RB4 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.03 | 89.82 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -9.98 | 86.86 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.60 | 82.26 |
| Structural A+ R3.5 RB4 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.08 | 90.34 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -9.93 | 86.36 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.57 | 81.79 |
| Structural A+ R3.5 RB6 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.03 | 89.82 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -9.98 | 86.86 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.60 | 82.26 |
| Structural A+ R3.5 RB6 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.08 | 90.34 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-06 | 2 | 0.00% | -2.12 | -9.93 | 86.36 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.57 | 81.79 |
| Structural A+ R3.5 RB8 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.03 | 89.82 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-06 | 2 | 0.00% | -2.12 | -9.98 | 86.86 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.60 | 82.26 |
| Structural A+ R3.5 RB8 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.08 | 90.34 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-06 | 1 | 0.00% | -1.04 | -5.03 | 91.26 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.83 | 86.43 |
| Structural A+ R4.0 RB4 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.48 | 94.91 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-06 | 1 | 0.00% | -1.04 | -5.06 | 91.79 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.86 | 86.93 |
| Structural A+ R4.0 RB4 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.53 | 95.46 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-06 | 1 | 0.00% | -1.04 | -5.03 | 91.26 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.83 | 86.43 |
| Structural A+ R4.0 RB6 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.48 | 94.91 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-06 | 1 | 0.00% | -1.04 | -5.06 | 91.79 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.86 | 86.93 |
| Structural A+ R4.0 RB6 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.53 | 95.46 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-04 | 1 | 100.00% | 1.48 | 6.99 | 101.71 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-05 | 1 | 0.00% | -1.06 | -5.41 | 96.29 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-06 | 1 | 0.00% | -1.04 | -5.03 | 91.26 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-07 | 1 | 0.00% | -1.06 | -4.83 | 86.43 |
| Structural A+ R4.0 RB8 FULL_3_5R | 2026-08 | 2 | 50.00% | 2.15 | 8.48 | 94.91 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-03 | 1 | 0.00% | -1.06 | -5.29 | 94.71 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-04 | 1 | 100.00% | 1.60 | 7.58 | 102.29 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-05 | 1 | 0.00% | -1.06 | -5.45 | 96.85 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-06 | 1 | 0.00% | -1.04 | -5.06 | 91.79 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-07 | 1 | 0.00% | -1.06 | -4.86 | 86.93 |
| Structural A+ R4.0 RB8 SCALE_25_2R_RUN4R | 2026-08 | 2 | 50.00% | 2.15 | 8.53 | 95.46 |
| Structural Portfolio 3.5R | 2026-01 | 4 | 0.00% | -4.22 | -19.51 | 80.49 |
| Structural Portfolio 3.5R | 2026-02 | 3 | 0.00% | -3.16 | -12.05 | 68.44 |
| Structural Portfolio 3.5R | 2026-03 | 5 | 40.00% | 3.83 | 11.91 | 80.35 |
| Structural Portfolio 3.5R | 2026-04 | 7 | 28.57% | 1.65 | 3.98 | 84.33 |
| Structural Portfolio 3.5R | 2026-05 | 5 | 40.00% | 3.66 | 13.81 | 98.14 |
| Structural Portfolio 3.5R | 2026-06 | 4 | 50.00% | 4.70 | 22.35 | 120.49 |
| Structural Portfolio 3.5R | 2026-07 | 6 | 33.33% | 2.64 | 12.64 | 133.14 |
| Structural Portfolio 3.5R | 2026-08 | 2 | 100.00% | 5.73 | 40.76 | 173.90 |
| Structural Portfolio 3.5R | 2026-09 | 2 | 50.00% | 2.40 | 19.28 | 193.18 |
| Structural Frequency STRICT_FVG | 2026-01 | 4 | 0.00% | -4.22 | -19.51 | 80.49 |
| Structural Frequency STRICT_FVG | 2026-02 | 4 | 0.00% | -4.19 | -15.59 | 64.90 |
| Structural Frequency STRICT_FVG | 2026-03 | 5 | 40.00% | 3.83 | 11.29 | 76.19 |
| Structural Frequency STRICT_FVG | 2026-04 | 7 | 28.57% | 1.65 | 3.77 | 79.96 |
| Structural Frequency STRICT_FVG | 2026-05 | 5 | 40.00% | 3.66 | 13.10 | 93.06 |
| Structural Frequency STRICT_FVG | 2026-06 | 4 | 50.00% | 4.70 | 21.20 | 114.26 |
| Structural Frequency STRICT_FVG | 2026-07 | 6 | 33.33% | 2.64 | 11.99 | 126.25 |
| Structural Frequency STRICT_FVG | 2026-08 | 2 | 100.00% | 5.73 | 38.65 | 164.90 |
| Structural Frequency STRICT_FVG | 2026-09 | 2 | 50.00% | 2.40 | 18.28 | 183.18 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-01 | 6 | 0.00% | -6.35 | -27.84 | 72.16 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-02 | 9 | 0.00% | -9.32 | -27.43 | 44.72 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-03 | 9 | 44.44% | 8.76 | 20.49 | 65.21 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-04 | 16 | 18.75% | -3.17 | -12.73 | 52.48 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-05 | 13 | 30.77% | 1.54 | 1.24 | 53.72 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-06 | 9 | 0.00% | -9.46 | -20.67 | 33.05 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-07 | 11 | 45.45% | 10.91 | 19.86 | 52.91 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-08 | 6 | 33.33% | 2.73 | 5.81 | 58.72 |
| Structural Frequency DISPLACEMENT_RETRACE | 2026-09 | 9 | 44.44% | 8.49 | 25.87 | 84.59 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-01 | 6 | 0.00% | -6.35 | -27.84 | 72.16 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-02 | 9 | 0.00% | -9.32 | -27.43 | 44.72 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-03 | 9 | 44.44% | 8.76 | 20.49 | 65.21 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-04 | 16 | 18.75% | -3.17 | -12.73 | 52.48 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-05 | 13 | 30.77% | 1.54 | 1.24 | 53.72 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-06 | 9 | 0.00% | -9.46 | -20.67 | 33.05 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-07 | 11 | 45.45% | 10.91 | 19.85 | 52.90 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-08 | 6 | 33.33% | 2.73 | 5.81 | 58.71 |
| Structural Frequency M15_LIQUIDITY_RETRACE | 2026-09 | 9 | 44.44% | 8.49 | 25.86 | 84.58 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-01 | 6 | 0.00% | -6.35 | -27.84 | 72.16 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-02 | 9 | 0.00% | -9.32 | -27.43 | 44.72 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-03 | 9 | 44.44% | 8.76 | 20.49 | 65.21 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-04 | 16 | 18.75% | -3.17 | -12.73 | 52.48 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-05 | 13 | 30.77% | 1.54 | 1.24 | 53.72 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-06 | 9 | 0.00% | -9.46 | -20.67 | 33.05 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-07 | 11 | 45.45% | 10.91 | 19.85 | 52.90 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-08 | 7 | 42.86% | 6.15 | 15.84 | 68.74 |
| Structural Frequency FULL_STRUCTURAL_ROUTER | 2026-09 | 9 | 44.44% | 8.49 | 30.28 | 99.02 |
| Structural Router QUALITY_CORE | 2026-01 | 2 | 0.00% | -2.14 | -10.41 | 89.59 |
| Structural Router QUALITY_CORE | 2026-02 | 4 | 0.00% | -4.20 | -17.38 | 72.21 |
| Structural Router QUALITY_CORE | 2026-03 | 4 | 25.00% | 0.35 | -0.01 | 72.21 |
| Structural Router QUALITY_CORE | 2026-04 | 2 | 0.00% | -2.13 | -7.49 | 64.72 |
| Structural Router QUALITY_CORE | 2026-05 | 5 | 40.00% | 3.66 | 10.60 | 75.32 |
| Structural Router QUALITY_CORE | 2026-06 | 4 | 0.00% | -4.26 | -14.80 | 60.52 |
| Structural Router QUALITY_CORE | 2026-07 | 2 | 0.00% | -2.13 | -6.27 | 54.25 |
| Structural Router QUALITY_CORE | 2026-08 | 1 | 100.00% | 2.26 | 6.14 | 60.39 |
| Structural Router QUALITY_CORE | 2026-09 | 1 | 100.00% | 3.43 | 10.37 | 70.75 |
| Structural Router LONDON_CORE | 2026-01 | 2 | 0.00% | -2.15 | -10.47 | 89.53 |
| Structural Router LONDON_CORE | 2026-02 | 3 | 0.00% | -3.16 | -13.41 | 76.12 |
| Structural Router LONDON_CORE | 2026-03 | 4 | 25.00% | 0.35 | -0.01 | 76.11 |
| Structural Router LONDON_CORE | 2026-04 | 2 | 0.00% | -2.13 | -7.89 | 68.22 |
| Structural Router LONDON_CORE | 2026-05 | 5 | 40.00% | 3.66 | 11.17 | 79.39 |
| Structural Router LONDON_CORE | 2026-06 | 4 | 0.00% | -4.30 | -15.74 | 63.65 |
| Structural Router LONDON_CORE | 2026-07 | 3 | 0.00% | -3.19 | -9.63 | 54.02 |
| Structural Router LONDON_CORE | 2026-08 | 1 | 100.00% | 2.26 | 6.12 | 60.14 |
| Structural Router LONDON_CORE | 2026-09 | 2 | 50.00% | 2.38 | 6.61 | 66.75 |
| Structural Router ROBUST_CORE | 2026-01 | 3 | 0.00% | -3.20 | -15.17 | 84.83 |
| Structural Router ROBUST_CORE | 2026-02 | 5 | 0.00% | -5.23 | -19.97 | 64.86 |
| Structural Router ROBUST_CORE | 2026-03 | 4 | 25.00% | 0.35 | -0.01 | 64.85 |
| Structural Router ROBUST_CORE | 2026-04 | 3 | 0.00% | -3.16 | -9.70 | 55.15 |
| Structural Router ROBUST_CORE | 2026-05 | 6 | 33.33% | 2.63 | 5.74 | 60.89 |
| Structural Router ROBUST_CORE | 2026-06 | 6 | 0.00% | -6.36 | -16.98 | 43.90 |
| Structural Router ROBUST_CORE | 2026-07 | 4 | 0.00% | -4.25 | -8.62 | 35.28 |
| Structural Router ROBUST_CORE | 2026-08 | 1 | 100.00% | 2.26 | 4.00 | 39.28 |
| Structural Router ROBUST_CORE | 2026-09 | 2 | 50.00% | 2.38 | 4.32 | 43.60 |
| Outcome First PB_BODY | 2026-01 | 2 | 0.00% | -2.13 | -10.35 | 89.65 |
| Outcome First PB_BODY | 2026-02 | 2 | 0.00% | -2.06 | -9.00 | 80.65 |
| Outcome First PB_BODY | 2026-03 | 2 | 0.00% | -2.06 | -8.08 | 72.57 |
| Outcome First PB_BODY | 2026-04 | 1 | 0.00% | -1.02 | -3.72 | 68.85 |
| Outcome First PB_BODY | 2026-05 | 2 | 50.00% | 2.42 | 7.72 | 76.57 |
| Outcome First PB_BODY | 2026-06 | 5 | 0.00% | -5.23 | -18.03 | 58.54 |
| Outcome First PB_BODY | 2026-07 | 2 | 0.00% | -2.10 | -5.99 | 52.55 |
| Outcome First PB_BODY | 2026-08 | 1 | 0.00% | -1.06 | -2.77 | 49.77 |
| Outcome First PB_BODY | 2026-09 | 2 | 0.00% | -2.09 | -5.07 | 44.70 |
| Outcome First PB_FVG | 2026-01 | 3 | 0.00% | -3.18 | -15.07 | 84.93 |
| Outcome First PB_FVG | 2026-02 | 1 | 0.00% | -1.03 | -4.40 | 80.54 |
| Outcome First PB_FVG | 2026-03 | 2 | 0.00% | -2.09 | -8.19 | 72.35 |
| Outcome First PB_FVG | 2026-05 | 1 | 100.00% | 3.42 | 12.37 | 84.72 |
| Outcome First PB_FVG | 2026-06 | 1 | 0.00% | -1.13 | -4.79 | 79.93 |
| Outcome First PB_FVG | 2026-07 | 1 | 0.00% | -1.06 | -4.24 | 75.69 |
| Outcome First SWEEP_FVG_LONDON | 2026-01 | 1 | 0.00% | -1.07 | -5.34 | 94.66 |
| Outcome First SWEEP_FVG_LONDON | 2026-02 | 2 | 0.00% | -2.13 | -9.82 | 84.84 |
| Outcome First SWEEP_FVG_LONDON | 2026-03 | 3 | 33.33% | 1.40 | 4.68 | 89.52 |
| Outcome First SWEEP_FVG_LONDON | 2026-04 | 3 | 0.00% | -3.19 | -13.51 | 76.00 |
| Outcome First SWEEP_FVG_LONDON | 2026-05 | 5 | 20.00% | -0.81 | -4.43 | 71.57 |
| Outcome First SWEEP_FVG_LONDON | 2026-06 | 3 | 33.33% | 1.34 | 3.74 | 75.31 |
| Outcome First SWEEP_FVG_LONDON | 2026-07 | 2 | 0.00% | -2.13 | -7.81 | 67.50 |
| Outcome First SWEEP_FVG_LONDON | 2026-08 | 1 | 100.00% | 2.26 | 7.64 | 75.15 |
| Outcome First SWEEP_FVG_LONDON | 2026-09 | 1 | 100.00% | 3.43 | 12.90 | 88.05 |
| Outcome First RETEST_BODY | 2026-01 | 1 | 0.00% | -1.05 | -5.26 | 94.74 |
| Outcome First RETEST_BODY | 2026-05 | 1 | 100.00% | 3.42 | 16.18 | 110.92 |
| Outcome First RETEST_BODY | 2026-06 | 1 | 0.00% | -1.06 | -5.88 | 105.04 |
| Outcome First RETEST_BODY | 2026-07 | 3 | 0.00% | -3.14 | -15.66 | 89.39 |
| Outcome First RETEST_BODY | 2026-09 | 1 | 100.00% | 3.44 | 15.37 | 104.76 |
| Outcome First RETEST_FVG | 2026-01 | 1 | 0.00% | -1.07 | -5.34 | 94.66 |
| Outcome First RETEST_FVG | 2026-07 | 1 | 0.00% | -1.04 | -4.92 | 89.75 |
| Outcome First CORE_PB_SWEEP | 2026-01 | 3 | 0.00% | -3.19 | -15.13 | 84.87 |
| Outcome First CORE_PB_SWEEP | 2026-02 | 4 | 0.00% | -4.19 | -16.44 | 68.42 |
| Outcome First CORE_PB_SWEEP | 2026-03 | 4 | 25.00% | 0.38 | 0.10 | 68.53 |
| Outcome First CORE_PB_SWEEP | 2026-04 | 4 | 0.00% | -4.21 | -13.32 | 55.20 |
| Outcome First CORE_PB_SWEEP | 2026-05 | 7 | 28.57% | 1.61 | 2.61 | 57.82 |
| Outcome First CORE_PB_SWEEP | 2026-06 | 8 | 12.50% | -3.89 | -11.31 | 46.51 |
| Outcome First CORE_PB_SWEEP | 2026-07 | 4 | 0.00% | -4.23 | -9.09 | 37.42 |
| Outcome First CORE_PB_SWEEP | 2026-08 | 2 | 50.00% | 1.21 | 2.04 | 39.46 |
| Outcome First CORE_PB_SWEEP | 2026-09 | 3 | 33.33% | 1.34 | 2.06 | 41.52 |
| Outcome First PORTFOLIO_BODY | 2026-01 | 4 | 0.00% | -4.25 | -19.60 | 80.40 |
| Outcome First PORTFOLIO_BODY | 2026-02 | 4 | 0.00% | -4.19 | -15.58 | 64.83 |
| Outcome First PORTFOLIO_BODY | 2026-03 | 4 | 25.00% | 0.38 | 0.10 | 64.93 |
| Outcome First PORTFOLIO_BODY | 2026-04 | 4 | 0.00% | -4.21 | -12.62 | 52.30 |
| Outcome First PORTFOLIO_BODY | 2026-05 | 7 | 28.57% | 1.61 | 2.47 | 54.78 |
| Outcome First PORTFOLIO_BODY | 2026-06 | 8 | 12.50% | -3.89 | -10.72 | 44.06 |
| Outcome First PORTFOLIO_BODY | 2026-07 | 5 | 0.00% | -5.27 | -10.46 | 33.61 |
| Outcome First PORTFOLIO_BODY | 2026-08 | 2 | 50.00% | 1.21 | 1.83 | 35.44 |
| Outcome First PORTFOLIO_BODY | 2026-09 | 4 | 50.00% | 4.78 | 8.27 | 43.70 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-01 | 4 | 0.00% | -4.26 | -19.67 | 80.33 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-02 | 4 | 0.00% | -4.19 | -15.56 | 64.77 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-03 | 4 | 25.00% | 0.38 | 0.10 | 64.87 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-04 | 4 | 0.00% | -4.21 | -12.61 | 52.26 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-05 | 7 | 28.57% | 1.61 | 2.47 | 54.73 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-06 | 8 | 12.50% | -3.89 | -10.71 | 44.02 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-07 | 5 | 0.00% | -5.27 | -10.44 | 33.58 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-08 | 2 | 50.00% | 1.21 | 1.83 | 35.41 |
| Outcome First PORTFOLIO_FVG_RETEST | 2026-09 | 3 | 33.33% | 1.34 | 1.85 | 37.26 |
| Route A Structural Asymmetric | 2026-01 | 7 | 0.00% | -7.39 | -31.59 | 68.41 |
| Route A Structural Asymmetric | 2026-02 | 10 | 10.00% | -7.34 | -21.82 | 46.58 |
| Route A Structural Asymmetric | 2026-03 | 9 | 44.44% | 6.76 | 15.62 | 62.21 |
| Route A Structural Asymmetric | 2026-04 | 16 | 18.75% | -3.67 | -13.23 | 48.97 |
| Route A Structural Asymmetric | 2026-05 | 14 | 35.71% | 2.30 | 3.47 | 52.44 |
| Route A Structural Asymmetric | 2026-06 | 9 | 0.00% | -9.46 | -20.18 | 32.27 |
| Route A Structural Asymmetric | 2026-07 | 12 | 58.33% | 10.35 | 19.28 | 51.54 |
| Route A Structural Asymmetric | 2026-08 | 8 | 37.50% | 1.60 | 2.87 | 54.41 |
| Route A Structural Asymmetric | 2026-09 | 9 | 66.67% | 13.49 | 46.26 | 100.67 |
| Route B Precision A+ | 2026-01 | 1 | 0.00% | -1.09 | -5.44 | 94.56 |
| V4 CORE | 2026-01 | 43 | 44.19% | -7.45 | -33.04 | 66.96 |
| V4 CORE | 2026-02 | 31 | 51.61% | -0.80 | -3.60 | 63.36 |
| V4 CORE | 2026-03 | 43 | 51.16% | -5.30 | -16.10 | 47.26 |
| V4 CORE | 2026-04 | 36 | 58.33% | 4.90 | 12.07 | 59.33 |
| V4 CORE | 2026-05 | 44 | 63.64% | 1.20 | 1.99 | 61.32 |
| V4 CORE | 2026-06 | 40 | 70.00% | 8.80 | 32.56 | 93.89 |
| V4 CORE | 2026-07 | 37 | 51.35% | -2.50 | -12.85 | 81.04 |
| V4 CORE | 2026-08 | 46 | 50.00% | -7.25 | -26.35 | 54.68 |
| V4 CORE | 2026-09 | 23 | 69.57% | 4.10 | 11.71 | 66.40 |
| V4 CORE SD SCORE60 | 2026-01 | 29 | 48.28% | -3.50 | -17.68 | 82.32 |
| V4 CORE SD SCORE60 | 2026-02 | 15 | 40.00% | -4.95 | -18.71 | 63.61 |
| V4 CORE SD SCORE60 | 2026-03 | 29 | 51.72% | -0.35 | -2.08 | 61.53 |
| V4 CORE SD SCORE60 | 2026-04 | 24 | 50.00% | 0.40 | 0.48 | 62.01 |
| V4 CORE SD SCORE60 | 2026-05 | 22 | 54.55% | -2.90 | -9.11 | 52.90 |
| V4 CORE SD SCORE60 | 2026-06 | 29 | 65.52% | 3.30 | 8.87 | 61.77 |
| V4 CORE SD SCORE60 | 2026-07 | 23 | 52.17% | 0.35 | 0.33 | 62.10 |
| V4 CORE SD SCORE60 | 2026-08 | 38 | 34.21% | -12.60 | -29.90 | 32.20 |
| V4 CORE SD SCORE60 | 2026-09 | 16 | 75.00% | 3.15 | 5.18 | 37.38 |
| V4 CORE SD SCORE65 | 2026-01 | 22 | 54.55% | -2.35 | -12.35 | 87.65 |
| V4 CORE SD SCORE65 | 2026-02 | 10 | 50.00% | -2.60 | -11.15 | 76.50 |
| V4 CORE SD SCORE65 | 2026-03 | 20 | 60.00% | -0.35 | -2.20 | 74.29 |
| V4 CORE SD SCORE65 | 2026-04 | 20 | 50.00% | 0.15 | -0.19 | 74.11 |
| V4 CORE SD SCORE65 | 2026-05 | 21 | 57.14% | -1.35 | -5.73 | 68.37 |
| V4 CORE SD SCORE65 | 2026-06 | 22 | 72.73% | 1.30 | 3.96 | 72.33 |
| V4 CORE SD SCORE65 | 2026-07 | 15 | 46.67% | -0.70 | -3.00 | 69.33 |
| V4 CORE SD SCORE65 | 2026-08 | 31 | 45.16% | -8.80 | -25.54 | 43.79 |
| V4 CORE SD SCORE65 | 2026-09 | 13 | 61.54% | 1.35 | 2.73 | 46.52 |
| V4 CORE SD M15 | 2026-01 | 35 | 48.57% | -3.65 | -18.61 | 81.39 |
| V4 CORE SD M15 | 2026-02 | 24 | 45.83% | -3.35 | -13.47 | 67.91 |
| V4 CORE SD M15 | 2026-03 | 40 | 50.00% | -4.40 | -14.86 | 53.06 |
| V4 CORE SD M15 | 2026-04 | 30 | 56.67% | 2.90 | 7.43 | 60.48 |
| V4 CORE SD M15 | 2026-05 | 33 | 54.55% | -4.35 | -12.83 | 47.66 |
| V4 CORE SD M15 | 2026-06 | 35 | 68.57% | 5.30 | 13.62 | 61.28 |
| V4 CORE SD M15 | 2026-07 | 29 | 44.83% | -4.10 | -12.20 | 49.08 |
| V4 CORE SD M15 | 2026-08 | 42 | 40.48% | -10.75 | -21.21 | 27.88 |
| V4 CORE SD M15 | 2026-09 | 17 | 70.59% | 1.60 | 2.05 | 29.92 |
| V4 CORE SD M15 SCORE60 | 2026-01 | 29 | 48.28% | -3.50 | -17.68 | 82.32 |
| V4 CORE SD M15 SCORE60 | 2026-02 | 15 | 40.00% | -4.95 | -18.71 | 63.61 |
| V4 CORE SD M15 SCORE60 | 2026-03 | 29 | 51.72% | -0.35 | -2.08 | 61.53 |
| V4 CORE SD M15 SCORE60 | 2026-04 | 24 | 50.00% | 0.40 | 0.48 | 62.01 |
| V4 CORE SD M15 SCORE60 | 2026-05 | 22 | 54.55% | -2.90 | -9.11 | 52.90 |
| V4 CORE SD M15 SCORE60 | 2026-06 | 29 | 65.52% | 3.30 | 8.87 | 61.77 |
| V4 CORE SD M15 SCORE60 | 2026-07 | 22 | 50.00% | -0.25 | -1.48 | 60.29 |
| V4 CORE SD M15 SCORE60 | 2026-08 | 38 | 34.21% | -12.60 | -29.03 | 31.26 |
| V4 CORE SD M15 SCORE60 | 2026-09 | 16 | 75.00% | 3.15 | 5.03 | 36.29 |
| V4 CORE SD M15 SCORE65 | 2026-01 | 22 | 54.55% | -2.35 | -12.35 | 87.65 |
| V4 CORE SD M15 SCORE65 | 2026-02 | 10 | 50.00% | -2.60 | -11.15 | 76.50 |
| V4 CORE SD M15 SCORE65 | 2026-03 | 20 | 60.00% | -0.35 | -2.20 | 74.29 |
| V4 CORE SD M15 SCORE65 | 2026-04 | 20 | 50.00% | 0.15 | -0.19 | 74.11 |
| V4 CORE SD M15 SCORE65 | 2026-05 | 21 | 57.14% | -1.35 | -5.73 | 68.37 |
| V4 CORE SD M15 SCORE65 | 2026-06 | 22 | 72.73% | 1.30 | 3.96 | 72.33 |
| V4 CORE SD M15 SCORE65 | 2026-07 | 14 | 42.86% | -1.30 | -5.02 | 67.31 |
| V4 CORE SD M15 SCORE65 | 2026-08 | 31 | 45.16% | -8.80 | -24.80 | 42.51 |
| V4 CORE SD M15 SCORE65 | 2026-09 | 13 | 61.54% | 1.35 | 2.65 | 45.16 |
| V4 QUALITY65 London/NY proxy | 2026-01 | 14 | 57.14% | 0.35 | 0.93 | 100.93 |
| V4 QUALITY65 London/NY proxy | 2026-02 | 7 | 57.14% | -1.15 | -6.13 | 94.79 |
| V4 QUALITY65 London/NY proxy | 2026-03 | 14 | 57.14% | -0.20 | -1.68 | 93.12 |
| V4 QUALITY65 London/NY proxy | 2026-04 | 12 | 25.00% | -2.50 | -11.44 | 81.68 |
| V4 QUALITY65 London/NY proxy | 2026-05 | 14 | 57.14% | -2.30 | -9.63 | 72.05 |
| V4 QUALITY65 London/NY proxy | 2026-06 | 15 | 80.00% | 1.95 | 6.96 | 79.01 |
| V4 QUALITY65 London/NY proxy | 2026-07 | 9 | 44.44% | -1.05 | -4.43 | 74.58 |
| V4 QUALITY65 London/NY proxy | 2026-08 | 19 | 36.84% | -7.85 | -25.03 | 49.55 |
| V4 QUALITY65 London/NY proxy | 2026-09 | 12 | 58.33% | 1.30 | 2.96 | 52.51 |

## Pine inventory not directly executable in GitHub Actions

GitHub Actions has no TradingView/Pine broker-emulator runtime. I therefore did **not fabricate Python results** for Pine files that do not have a maintained Python parity engine. Exact Pine-only items still requiring TradingView Strategy Tester are:

- `pine/CASIO_XAUUSD_v1.pine` — Pine-only legacy implementation.
- `pine/CASIO_XAUUSD_v2_MTF.pine` — Pine-only MTF implementation.
- `pine/CASIO_XAUUSD_v5_MTF.pine` — Pine-only M15-setup/M5-execution challenger; no maintained Python parity engine yet.
- `pine/CASIO_XAUUSD_TRADING_ASSISTANT.pine` and `pine/CASIO_XAUUSD_M5_FEED.pine` are indicators/feed helpers rather than independent Python backtest engines.

`CASIO_XAUUSD_v3_BACKTEST.pine` / `v3_FAST.pine` are represented by the V3 M5 Python engine family; v4 is represented by the v4 confluence Python replay variants.

## Audit files

- `comparison.csv` — one row per strategy/variant.
- `monthly.csv` — month-by-month results.
- `all_trades.csv` — normalized 2026 trade/equity rows used for the RM100/5% calculation.

This is research evidence, not a guarantee of future profitability. Many variants are closely related, so a high result from one profile is not independent confirmation by itself.
