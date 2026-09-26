# Finotive Multi-Pair Research Plan

Status: research only. No live strategy changes.

## Data sources

Use only the user-supplied FxPro M1 datasets:
- XAUUSD M1
- GBPUSD M1
- GBPJPY M1

Do not substitute Dukascopy for this research.

## Hard objective

A candidate portfolio is accepted only if, on completed holdout months:
- realized return >= +5% every month,
- at least 5 profitable days per payout cycle/month, each >= +0.5% of initial balance,
- zero 3% daily drawdown hard breaches,
- zero 6% maximum drawdown hard breaches,
- fixed 1:3 reward:risk,
- real stop loss only,
- no breakeven/protected-SL accounting,
- no martingale, recovery sizing, averaging losers or grid,
- at most one active trade per symbol,
- two realized losses in one trading day => stop trading for that day.

## Risk architecture

Base risk per trade: 0.5% maximum.

Correlation clusters:
- GBPUSD and GBPJPY belong to one GBP cluster. Combined simultaneous risk across them must not exceed 0.5%.
- XAUUSD is a separate cluster.
- Total simultaneous portfolio risk should not exceed 1.0%.
- When two GBP signals overlap, either take the higher-quality signal only or split the 0.5% cluster risk.

This prevents apparent diversification from becoming duplicated GBP exposure.

## Validation protocol

- 2017-2022: discovery only.
- 2023-2025: validation / rule selection.
- 2026: untouched holdout for final monthly-floor test.
- Do not tune a rule after viewing a failing 2026 month and then re-label 2026 as untouched OOS.

## Pair-specific research families

### GBPUSD
1. London open liquidity sweep -> reclaim -> M5/M15 confirmation.
2. London directional drive -> New York continuation/retest.
3. London-NY overlap breakout/retest with H1/H4 direction.
4. Previous-day high/low sweep during London/NY.
5. Asian compression -> London expansion.

### GBPJPY
1. Tokyo/Asia directional drive -> London continuation/reversal router.
2. Asia high/low sweep -> M5/M15 displacement.
3. Tokyo-London handoff continuation with H1/H4 alignment.
4. London breakout/retest after Asia compression.
5. Previous-day high/low sweep with session confirmation.

### XAUUSD
Keep only historically defensible sleeves already discovered:
- RR10 / 0591 family,
- strict Asia-drive -> London continuation sleeve,
- validated session/liquidity sleeves.

## Portfolio construction

Do not simply union every profitable strategy.
A multi-pair portfolio must:
1. preserve one-active-trade-per-symbol,
2. respect GBP cluster risk,
3. resolve simultaneous signals by quality score / historical validation,
4. target complementary monthly P&L rather than maximizing average return,
5. stop opening new risk after the monthly payout target is reached and the profitable-day requirement is satisfied.

Primary ranking metric:
1. number of completed months >= +5%,
2. worst completed month,
3. number of payout-ready months,
4. hard-breach count,
5. max drawdown,
6. average monthly return.

Average return is deliberately not the primary objective.
