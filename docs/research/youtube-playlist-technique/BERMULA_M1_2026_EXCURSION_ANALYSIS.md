# Bermula M1 2026 — Excursion / RR Trace

Updated: 2026-09-24

## Objective

Freeze the already-identified 2026 Bermula continuation entries and structural stops, remove the structural take-profit assumption, and trace how far every confirmed setup travelled in the favorable direction before the real stop was hit.

This directly answers the exit question: **what R multiple was actually available from each setup?**

## Data and scope

- Source: user-supplied `fxpro_xauusd_m1.csv`
- Instrument: XAUUSD
- Execution resolution: M1
- Only 2026 entries
- Full pre-2026 history used causally for Bermula/S&R context
- 11 strong breakout candidates in 2026
- 10 completed breakout -> pullback -> M1 confirmation setups
- 1 breakout candidate (2026-05-15) never produced the required pullback and is not treated as an entry setup
- No TP is imposed while measuring excursion
- Same structural stops as the prior M1 backtest
- All 10 entered setups eventually touched the structural stop

## Measurement rule

For each setup:

```text
R = |entry - structural stop|
MFE(R) = maximum favorable move from entry / R
```

The first M1 stop-touch bar is excluded from favorable excursion measurement. Therefore if target and stop could both have occurred inside the same M1 candle, the analysis is conservative and treats that candle as stop-first rather than crediting an ambiguous target.

## Every 2026 setup

| # | Entry UTC | Side | Entry | Stop | Best price before stop | Max R | Time of max | Strict H4 direction? |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | Jan 30 10:08 | Short | 5011.22 | 5101.92 | 5001.09 | **0.112R** | Jan 30 10:08 | No |
| 2 | Feb 24 14:12 | Short | 5113.64 | 5166.13 | 5094.24 | **0.370R** | Feb 24 14:13 | No |
| 3 | Mar 23 09:33 | Short | 4287.53 | 4344.05 | 4223.79 | **1.128R** | Mar 23 09:45 | No |
| 4 | Apr 07 23:04 | Long | 4821.27 | 4748.08 | 4857.73 | **0.498R** | Apr 08 00:06 | No |
| 5 | Apr 20 00:52 | Short | 4760.88 | 4803.74 | 4759.49 | **0.032R** | Apr 20 00:52 | No |
| 6 | Apr 28 10:49 | Short | 4611.77 | 4672.68 | 4501.05 | **1.818R** | May 04 16:10 | No |
| 7 | May 05 09:01 | Short | 4555.15 | 4584.81 | 4539.69 | **0.521R** | May 05 11:01 | Yes |
| 8 | Jun 10 12:11 | Short | 4140.01 | 4181.26 | 4130.65 | **0.227R** | Jun 10 12:27 | Yes |
| 9 | Jul 22 02:23 | Long | 4125.11 | 4106.96 | 4141.68 | **0.913R** | Jul 22 03:23 | No |
| 10 | Aug 21 09:38 | Long | 4585.02 | 4553.23 | 4696.99 | **3.523R** | Aug 25 00:42 | No |

## Excursion distribution

- Minimum MFE: **0.032R**
- 25th percentile: **0.263R**
- Median: **0.510R**
- Mean: **0.914R**
- 75th percentile: **1.074R**
- Maximum: **3.523R**

Coverage:

| Fixed target | Setups reaching it before SL | Hit rate | Gross result if every setup used that target |
|---:|---:|---:|---:|
| 0.10R | 9 / 10 | 90% | -0.10R |
| 0.20R | 8 / 10 | 80% | -0.40R |
| 0.25R | 7 / 10 | 70% | -1.25R |
| 0.35R | 7 / 10 | 70% | -0.55R |
| 0.50R | 5 / 10 | 50% | -2.50R |
| 0.75R | 4 / 10 | 40% | -3.00R |
| **1.00R** | **3 / 10** | **30%** | **-4.00R** |
| 1.50R | 2 / 10 | 20% | -5.00R |
| **2.00R** | **1 / 10** | **10%** | **-7.00R** |
| **3.00R** | **1 / 10** | **10%** | **-6.00R** |

## Exact in-sample optimum

If target R is allowed to be any arbitrary number chosen after observing these same 10 trades, the mathematical maximum occurs immediately below the smallest MFE:

- target ≈ **0.0324R**
- 10 / 10 targets hit
- gross total ≈ **+0.324R**
- after a 1 bp round-trip sensitivity: ≈ **+0.214R**

This is **not a robust exit choice**. A 0.032R target requires roughly a 97%+ win rate merely to survive one full -1R loss, and the value is selected directly from the smallest observed excursion. It should be recorded as the mathematical in-sample optimum, not promoted as a trading rule.

At the next excursion boundary (~0.112R), hit rate becomes 9/10 and the gross result is essentially flat (+0.005R before execution friction, negative after 1 bp).

## Practical fixed-RR result

On a conventional grid, no tested fixed R multiple is profitable with the current structural stop definition.

Among targets >= 0.25R, the least-negative result is around **0.35R**:

- 7 / 10 winners
- 70% WR
- -0.55R gross
- about -0.66R with 1 bp sensitivity

Therefore there is no defensible positive fixed RR to select yet from the all-setup pool.

## What this tells us

The exit study changes the diagnosis.

The earlier nearest-S/R target was not the only problem. Even when TP is removed entirely and each trade is allowed to travel until the structural stop, most setups do not generate a large R multiple because the current risk denominator is wide.

Only:
- 3/10 reached 1R,
- 2/10 reached 1.5R,
- 1/10 reached 2R,
- 1/10 reached 3R.

The current stop is placed beyond the H4 Bermula zone. Paul-X teaches structural risk management, but the supplied material has not yet proved that this exact H4-zone stop is his universal execution stop. If his actual execution SL is tied to the nested lower-timeframe confirmation/Bermula zone, the R distribution could change materially.

That is now the highest-value variable to resolve. Do **not** alter the entries or optimize a TP around these 10 trades before resolving the actual stop anchor.

## Strict-direction subset

Only setups #7 and #8 satisfy the current HH/HL-LH/LL direction translation.

Their MFE was:
- 0.521R
- 0.227R

With only two observations, that subset is not large enough to choose an exit ratio.

## Files

- `BERMULA_M1_2026_EXCURSION_ANALYSIS.md`
- `bermula_m1_2026_setup_excursions.csv`
- `bermula_m1_2026_rr_sweep.csv`

Research branch: `research/youtube-playlist-technique`
