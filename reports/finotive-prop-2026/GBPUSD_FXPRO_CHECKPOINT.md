# GBPUSD FxPro M1 — Research Checkpoint

Source: user-uploaded `fxpro_gbpusd_m1.csv` (FxPro M1).
Coverage verified in runtime: 2017-01-01 through 2026-09-24.

## Hard rules

- Pair-neutral project objective, but this checkpoint is GBPUSD-only.
- Fixed 1:3 reward:risk.
- Hard SL only.
- No BE/protected SL.
- No martingale, recovery sizing, averaging losers, or grid.
- Max risk target: 0.5% per trade.
- One active position per strategy/symbol.
- Maximum two realized losses per day.
- MTF required.
- Primary objective: >=5% every completed month; target 8-10%.

## Validation protocol

- 2017-2022 discovery.
- 2023-2025 validation.
- 2026 holdout.
- Do not tune a rule after seeing 2026 and relabel the same period as untouched OOS.

## Execution assumptions

- Higher-timeframe features use completed bars only.
- Signals evaluated on M15/M5 depending on family.
- Entry occurs on the next available M1 bar after confirmation.
- SL/TP replayed on FxPro M1.
- Fixed target = 3R.
- Conservative friction was included in the research passes.
- Stop-first treatment where an SL/TP collision is ambiguous.
- DST-aware London/New York session labels.

## Families rejected so far

The following did not show sufficiently stable positive expectancy across both discovery and validation:
- canonical RR10/0591 on GBPUSD,
- reverse RR10,
- London->NY continuation breakout,
- generic Asia->London continuation breakout,
- previous-day sweep,
- generic M15 EMA pullback,
- M15 displacement continuation,
- London/NY opening-range breakout,
- M15 tick-volume momentum,
- M15 ADX/DI momentum,
- M15 H1/H4 trend pullback,
- M5 trend displacement,
- M5 trend pullback.

Several of these looked attractive in 2026 alone but were negative or unstable in 2017-2025 and were therefore rejected.

## Strongest robust family so far

### M5 Asia false-break fade — first valid signal/day, body >= 0.35

Concept:
- Build the Asian range.
- During the London window, price sweeps one side of the Asian range.
- Candle closes back inside the range in the reversal direction.
- Use M15/H1/H4 context as research features.
- Take only the first valid fade signal of the day.
- Structural hard SL beyond the sweep candle.
- Fixed 3R TP.
- M1 execution.

Observed expectancy:

| Period | Trades | Exp R/trade | PF | Positive months |
|---|---:|---:|---:|---:|
| 2017-2022 | 1,044 | +0.048R | 1.06 | 36/72 |
| 2023-2025 | 512 | +0.155R | 1.21 | 21/36 |
| 2026 Jan-Aug | 120 | +0.160R | 1.22 | 7/8 |

This is a real improvement in stability versus the other tested GBPUSD families, but it does NOT satisfy the monthly payout objective at 0.5% risk.

## Filter study

Pre-2026-only filter analysis found some stable context effects:
- earlier London entries (before ~09:30 local) improve stability,
- stronger close-back-inside-range confirmation helps,
- body >=0.50 improves 2023-2025 expectancy,
- moderate Asian-range size can improve the filtered sample,
- very low H4 ADX can be useful in some fade subsets.

However, filtering raises expectancy by reducing frequency. Even the better pre-2026 filtered variants remain well below the ~+10R/month required for +5% return at 0.5% risk.

## Current conclusion

GBPUSD has at least one defensible mean-reversion/fade edge, but no tested GBPUSD-only engine currently meets:
- every month >= +5%, or
- target +8-10% monthly,
under the fixed 3R / max 0.5% risk framework.

Next research should focus on genuinely higher-frequency MTF execution (M3/M5) and independent GBPUSD sleeves rather than adding more filters to the same Asia-fade signal.
