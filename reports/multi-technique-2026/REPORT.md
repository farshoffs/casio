# CASIO Multi-Technique Ensemble Test — 2026

## Fixed test rule

- Source: `data/xauusd_m5_dukascopy_research.csv`.
- Test window: **2026-01-01 through 2026-09-16T13:30:00+00:00**.
- One shared account per ensemble, starting **RM100**.
- Risk **5% of current account balance** on each accepted trade.
- Require **at least 8 filled trades in every completed month**.
- 1 bp round-trip cost; source techniques keep their frozen 2R/3R/4R target logic.
- Only one portfolio position may be open at a time. Overlapping source signals are skipped or routed by the ensemble rule.
- No weight/threshold grid search was performed for the ensemble. These are five transparent combination rules.

## Source techniques

1. M15-0591 MTF
2. Outcome First M15
3. V1 Legacy M15
4. Structural Portfolio MTF
5. Structural Frequency M15

## Combination methods

- **ANY-FIRST**: first available signal wins; fixed priority breaks same-bar collisions.
- **PRIORITY-VETO**: same as a stack, but a recent opposite signal from an equal/higher-priority technique vetoes the candidate.
- **CONSENSUS-2**: requires at least two distinct techniques agreeing in the prior 30 minutes and more agreement than opposition.
- **CORE+BOOSTER**: M15-0591 MTF + Structural Portfolio MTF are the core. Booster techniques need core support or agreement from another booster; opposite core signals veto.
- **REGIME-ROUTER**: strong aligned H1/H4 trend favors momentum/breakout techniques; mixed regimes favor structural techniques. No future HTF data is used.

## Results

| variant                  | type     |   trades |   trades_per_30d |   min_completed_month_trades |   ending_balance_rm |   lowest_balance_rm | passes_frequency   | passes_growth   | requested_fit   |
|:-------------------------|:---------|---------:|-----------------:|-----------------------------:|--------------------:|--------------------:|:-------------------|:----------------|:----------------|
| REGIME-ROUTER            | ensemble |      284 |          32.9514 |                           27 |             842.285 |             75.4496 | True               | True            | True            |
| PRIORITY-VETO            | ensemble |      429 |          49.7752 |                           45 |             734.004 |             75.903  | True               | True            | True            |
| ANY-FIRST                | ensemble |      432 |          50.1233 |                           45 |             627.799 |             75.903  | True               | True            | True            |
| M15-0591 MTF             | single   |      238 |          27.6142 |                           21 |             419.753 |             42.175  | True               | True            | True            |
| Outcome First M15        | single   |      121 |          14.0392 |                           10 |             419.596 |             94.9061 | True               | True            | True            |
| V1 Legacy M15            | single   |      321 |          37.2444 |                           31 |             345.8   |             69.0675 | True               | True            | True            |
| CORE+BOOSTER             | ensemble |      309 |          35.8521 |                           30 |             303.097 |             72.7646 | True               | True            | True            |
| CONSENSUS-2              | ensemble |      105 |          12.1827 |                            8 |             297.807 |            100      | True               | True            | True            |
| Structural Portfolio MTF | single   |      124 |          14.3872 |                           10 |             258.153 |             92.6531 | True               | True            | True            |
| Structural Frequency M15 | single   |      113 |          13.1109 |                            8 |             237.784 |             93.3058 | True               | True            | True            |

## Best ensemble under the requested test

**REGIME-ROUTER**: RM100 -> **RM842.28**, 284 trades, minimum **27** trades in a completed month. Requested fit: **PASS**.

## Technique contribution to each ensemble

| ensemble      | technique                |   trades |
|:--------------|:-------------------------|---------:|
| ANY-FIRST     | V1 Legacy M15            |      188 |
| ANY-FIRST     | M15-0591 MTF             |      118 |
| ANY-FIRST     | Structural Portfolio MTF |       57 |
| ANY-FIRST     | Outcome First M15        |       44 |
| ANY-FIRST     | Structural Frequency M15 |       25 |
| PRIORITY-VETO | V1 Legacy M15            |      186 |
| PRIORITY-VETO | M15-0591 MTF             |      118 |
| PRIORITY-VETO | Structural Portfolio MTF |       57 |
| PRIORITY-VETO | Outcome First M15        |       43 |
| PRIORITY-VETO | Structural Frequency M15 |       25 |
| CONSENSUS-2   | Structural Portfolio MTF |       48 |
| CONSENSUS-2   | M15-0591 MTF             |       23 |
| CONSENSUS-2   | Outcome First M15        |       21 |
| CONSENSUS-2   | V1 Legacy M15            |       12 |
| CONSENSUS-2   | Structural Frequency M15 |        1 |
| CORE+BOOSTER  | M15-0591 MTF             |      194 |
| CORE+BOOSTER  | Structural Portfolio MTF |       95 |
| CORE+BOOSTER  | Outcome First M15        |       13 |
| CORE+BOOSTER  | V1 Legacy M15            |        7 |
| REGIME-ROUTER | Structural Portfolio MTF |       81 |
| REGIME-ROUTER | V1 Legacy M15            |       67 |
| REGIME-ROUTER | Outcome First M15        |       47 |
| REGIME-ROUTER | Structural Frequency M15 |       46 |
| REGIME-ROUTER | M15-0591 MTF             |       43 |

## Dashboard implication

The five techniques should remain visible as separate dashboard modules. The ensemble layer should sit above them and show: each technique's direction, its target R, H1/H4 context, recent agreement/opposition, which router rule is active, and the final portfolio action. This preserves transparency instead of hiding the techniques inside one opaque score.

## Research status

This is an exploratory 2026 combination test built after seeing the individual 2026 results. It is useful for selecting dashboard architecture, but any chosen ensemble must be frozen and validated on earlier unseen years / the independent feed before being treated as robust.