# FxPro Pair-Neutral Prop Research Checkpoint — 2026-09-26

## Objective

Pair-neutral prop research. No permanent core symbol.

Preferred completed-month return: +8% to +10%.
Acceptance floor: +5% every completed month.

Hard research rules:
- FxPro source data only.
- Fixed 1:3 reward:risk.
- Maximum 0.5% equity risk per trade.
- Real structural stop only.
- No breakeven/protected-SL accounting.
- No martingale, grid, averaging losers, or recovery sizing.
- MTF context required.
- Max two realized losses per day.
- 2017-2022 discovery.
- 2023-2025 validation / rule selection.
- 2026 holdout.

## Data

FxPro M1 datasets:
- XAUUSD: 2017-01-02 through 2026-09-24.
- GBPUSD: 2017-01-01 through 2026-09-24.
- GBPJPY: 2017-01-01 through 2026-09-24.
- EURUSD: 2017-01-01 through 2026-09-24.

Dukascopy is not used for these findings.

## Important audit correction

An early GBPUSD M5 run produced implausibly strong 2026 returns. Trade-level audit found variable shadowing: the M1-low price array was overwritten by a boolean long-signal mask before execution replay. That invalidated stop-loss detection.

Those results are permanently rejected.

All findings below use the corrected M1 execution arrays.

## GBPUSD

Corrected M5 continuation/pullback/range-sweep/opening-range families:
- No candidate passed discovery + validation robustness.

MTF London-to-New-York fade:
- LONNY_FADE_align2_b0.25
- 2017-2022: 70 trades, expectancy +0.186R, PF 1.254.
- 2023-2025: 43 trades, expectancy +0.210R, PF 1.286.
- 2026 returns at 0.5% risk: Jan -0.54%, Feb -0.52%, Mar -0.09%, Apr 0.00%, May -0.54%, Jun -0.55%, Jul -1.14%, Aug -0.56%.
- Rejected as payout engine.

M15 Donchian:
- DON_P_a1_n40
- 2017-2022 expectancy +0.139R.
- 2023-2025 expectancy +0.199R.
- 2026: +2.42%, 0.00%, -1.04%, -3.09%, -2.10%, -0.64%, -0.14%, +2.94%.
- Rejected.

M15 volume continuation:
- VOL_a1_v1.2_r0.8
- Pre-2026 positive but weak.
- 2026 mostly negative; rejected.

Causal monthly normal/reverse router:
- 12-month lookback selected without using current month.
- 2023-2025: 117 trades, expectancy +0.220R, PF 1.309, all 3 years positive.
- 2026 monthly returns:
  - Jan -0.52%
  - Feb +0.95%
  - Mar +0.88%
  - Apr +0.39%
  - May +2.43%
  - Jun +4.38%
  - Jul -1.57%
  - Aug -1.10%
- Best month still below +5%; rejected as standalone payout engine.

Retracement-entry Donchian:
- DON_ret0.4_x45
- Discovery + validation positive.
- 2026: +2.41%, -1.55%, -2.57%, -0.64%, +0.28%, -1.69%, -1.07%, +0.73%.
- Rejected.

Fixed session impulse:
- Several low-frequency pre-2026 positive variants survived.
- Returns were generally around +/-1.5% monthly in 2026, far below payout target.
- Rejected as standalone engine.

London-fix / intraday-seasonality MTF families:
- Domestic-session drift, post-London drift, and 4pm London-fix reversal tested.
- Zero candidates survived discovery + validation.

## GBPJPY

Corrected M5 generic families:
- No stable discovery + validation candidates.

M15 ADX / volume / Donchian / compression:
- No stable candidates.

Tokyo-to-London pair-specific continuation/fade:
- No stable candidates.

Conclusion: no validated GBPJPY sleeve currently qualifies for portfolio inclusion.

## EURUSD

Corrected M5 generic families:
- No stable discovery + validation candidates.

M15 ADX / volume / Donchian / compression:
- No stable candidates.

London-fix / intraday-seasonality MTF families:
- Zero stable candidates.

## Cross-pair / pair-neutral tests

EURUSD <-> GBPUSD lead-lag / relative-strength continuation:
- Pair selected from normalized M15 momentum with common H1/H4 USD direction.
- Zero candidates survived 2017-2022 discovery + 2023-2025 validation.

Four-symbol cross-sectional daily selector:
- Symbols: XAUUSD, GBPUSD, GBPJPY, EURUSD.
- Pair chosen daily by best MTF-valid Asia->London or London->NY breakout quality.
- One selected opportunity rather than a permanent core pair.
- Zero candidates survived discovery + validation.

Failed-breakout / exhaustion reversal family:
- Tested consistently on all four symbols.
- Donchian false-break reversal, volume/range climax fade, and EMA stretch rejection with H1/H4 gate.
- Zero stable candidates on all four symbols.

## Portfolio sufficiency check

A deliberately over-optimistic oracle screen was used only as an impossibility check, not as a deployable backtest.

The screen:
- chooses the better known XAU sleeve for each 2026 month with hindsight;
- then adds every positive validated GBPUSD sleeve for that month even when overlap/risk rules would prevent taking all of them.

Even this unrealistic upper bound produced approximately:
- Jan +15.85%
- Feb +3.36%
- Mar +5.38%
- Apr +3.87%
- May +7.12%
- Jun +15.71%
- Jul +2.92%
- Aug +8.34%

Therefore the current tested candidate universe cannot explain a +5% floor in February, April, and July 2026 even under favorable impossible aggregation. A legal risk-constrained portfolio cannot be expected to exceed that optimistic screen using the same sleeves.

## Current conclusion

No tested static, adaptive, pair-specific, cross-pair, or cross-sectional system has met the user's minimum +5% completed-month floor while preserving the fixed 3R / <=0.5% risk / real-SL / no-BE / no-martingale rules.

The research problem is now edge discovery rather than portfolio routing. Further work should add genuinely different information or markets rather than repeatedly optimize the rejected rule families against 2026.
