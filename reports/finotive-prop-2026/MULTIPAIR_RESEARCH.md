# Finotive Multi-Pair Research Plan

Status: research only. No live strategy changes.

## Data sources

Primary research sources:
- user-supplied FxPro XAUUSD M1,
- user-supplied FxPro GBPUSD M1.

GBPJPY remains an optional future diversification dataset and must not be treated as available unless a matching user-supplied FxPro file is present.

Do not substitute Dukascopy for final FxPro acceptance testing.

## Hard objective — revised 26 Sep 2026

A candidate portfolio is accepted only if, on every completed holdout month:
- realized return >= +8%,
- +10% is the stretch objective,
- at least 5 profitable days per payout cycle/month, each >= +0.5% of initial balance,
- zero 3% daily drawdown hard breaches,
- zero 6% maximum drawdown hard breaches,
- zero avoidable 1.5% floating-drawdown threshold events,
- real stop loss only,
- no martingale, recovery sizing, averaging losers or grid,
- no dependence on one outsized trade or one-sided concentration,
- two realized losses in one trading day => stop opening new trades for that day.

Reward:risk is a research variable where appropriate. Existing RR10 remains fixed at 3R; new sleeves may test bounded 2R/2.5R/3R alternatives using discovery/validation data only.

## Account economics — USD 2,500 Lite

- +8% = +USD 200.
- +10% = +USD 250.
- 0.5% initial-balance profitable-day threshold = USD 12.50.
- 3% daily drawdown = USD 75 at the initial balance.
- 6% static maximum drawdown = USD 150 from the initial balance.
- 1.5% floating-drawdown threshold = USD 37.50 of combined unrealised loss.

The portfolio therefore targets return through independent expectancy rather than forcing higher per-trade risk.

## Risk architecture

Baseline research risk per trade: 0.5% maximum.

Correlation / concurrency:
- Prefer one active portfolio position at a time while proving the model.
- If simultaneous independent positions are later allowed, combined hard-stop risk must remain <=1.0%.
- Treat multiple trades expressing the same underlying idea as one risk cluster.
- When correlated signals overlap, take the higher-quality signal or split risk rather than duplicate full risk.

## Validation protocol

- 2017-2022: discovery only.
- 2023-2025: validation / rule selection.
- 2026: untouched holdout for final monthly-floor test.
- Do not tune a rule after viewing a failing 2026 month and then re-label 2026 as untouched OOS.

## Existing pair-specific evidence

### GBPUSD

Already tested / rejected as standalone robust engines:
1. 0591 continuation.
2. London -> New York continuation.
3. Asia -> London continuation.
4. generic previous-day sweep.
5. generic EMA trend pullback.
6. generic displacement continuation.
7. London/NY opening-range fakeout.
8. previous-week high/low sweep.

Validated complementary candidates:
- Asia-range false-break fade during London.
- London-drive -> New York false-break/exhaustion.

These have useful expectancy but do not meet the +8% monthly floor by themselves.

### XAUUSD

Keep only historically defensible sleeves as baselines:
- RR10 / 0591 regime-router family,
- validated structural/liquidity sleeves.

The previous 2026 prop sweep also tested structural/FVG, EMA pullback, volume continuation, 24-bar momentum, Asia sweep, previous-day sweep and Asia breakout families. None met the old +8% requirement in every completed month at 0.4–0.5% risk.

## Phase 2 new research families

1. Daily Range Extension Reversion (XAUUSD + GBPUSD).
2. Asymmetric D1/H4 trend pullback (XAUUSD + GBPUSD).
3. Compression -> expansion -> first pullback (XAUUSD + GBPUSD).
4. Failed-breakout second-entry fade.
5. Volatility-regime router that selects among frozen sleeves or WAIT.

See `NEXT_EDGE_HUNT.md` for exact hypotheses.

## Portfolio construction

Do not simply union every profitable strategy.

A portfolio must:
1. preserve the risk limits above,
2. resolve simultaneous/correlated signals,
3. target complementary monthly P&L rather than maximizing average return,
4. stop opening new risk after the +5% floor and profitable-day requirement are both satisfied,
5. avoid depending on low-liquidity-window exploitation,
6. preserve frozen parameters before the 2026 holdout.

Primary ranking metric:
1. number of completed months >= +8%,
2. worst completed month,
3. number of payout-ready months,
4. floating-DD threshold-event count,
5. hard-breach count,
6. max drawdown,
7. average monthly return.

Average return is deliberately not the primary objective.
