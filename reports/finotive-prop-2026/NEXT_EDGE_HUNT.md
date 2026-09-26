# Finotive Instant Lite — Phase 2 Edge Hunt

Status: research only. Branch: `research/finotive-prop`.

## Objective

Account: USD 2,500 Finotive Instant Funding Lite.

Target objective:
- +8% to +10% realized account return per payout cycle/month;
- 5 qualifying profitable days;
- zero 3% daily drawdown hard breaches;
- zero 6% static maximum drawdown hard breaches;
- avoid 1.5% floating-drawdown threshold events;
- no martingale, grid, averaging losers, recovery sizing, or protected/virtual stop accounting.

The target is an acceptance criterion, not an assumption that a strategy must be forced to produce it.

## Current evidence

### XAUUSD

RR10 remains the strongest existing high-frequency XAUUSD sleeve in the repository:
- roughly 6.3–8.0 trades / 30 days in 2024–2026;
- fixed 3R;
- 2025 expectancy about +0.77R/trade;
- 2026 YTD expectancy about +0.74R/trade.

At 0.5% risk, ~8 trades/month × ~0.74R expectancy is only ~+3% expected monthly return before real-world execution differences. Increasing risk enough to force +8% would place individual-trade risk too close to the Lite floating-drawdown threshold and would make ordinary loss streaks incompatible with the 6% static drawdown cap.

The 2026 prop research sweep also tested structural/FVG variants, EMA pullback, volume continuation, 24-bar momentum, Asia sweep, previous-day sweep, Asia breakout and combinations. None produced +8% in every completed 2026 month at 0.4–0.5% risk.

### GBPUSD — user FxPro M1

The current FxPro checkpoint rejected the symmetric continuation families:
- 0591 continuation;
- London -> New York continuation;
- Asia -> London continuation;
- previous-day continuation/sweep variants;
- EMA trend pullback;
- generic displacement continuation.

The first repeatable GBPUSD family was an Asia-range false-break fade during London.

Baseline 2026 at 0.5% risk:
- Jan +6.40%
- Feb +4.21%
- Mar +2.69%
- Apr -0.28%
- May +3.23%
- Jun +2.69%
- Jul +2.16%
- Aug -4.27%

This is useful as a complementary mean-reversion sleeve, but it does not satisfy the monthly floor by itself.

The higher-quality Asia-fade filter and New York exhaustion filter improved expectancy, but frequency became too low.

## Required portfolio economics

At 0.5% risk:
- +8% requires approximately +16R net;
- +10% requires approximately +20R net.

Therefore the research problem is not “find a higher-risk version of RR10.” It is:

> add independent positive-expectancy sleeves until the portfolio can generate approximately 16–20R in a strong payout cycle without relying on correlated risk or breaching the Lite risk envelope.

## Phase 2 candidate families

### A. Daily Range Extension Reversion (DRE)

Purpose: add a mean-reversion sleeve that is structurally different from Asia-range fade.

Candidate logic:
1. Build prior 20-day ADR and daily ATR causally.
2. Measure current-day range utilization and extension beyond PDH/PDL.
3. Trigger only after price has used roughly 0.8–1.2 ADR and sweeps external daily liquidity.
4. Require a close/reclaim back through the swept level.
5. Reject fades when H4/H1 trend expansion is strongly aligned with the breakout.
6. Require M5 displacement/MSS away from the extreme.
7. Enter on 38–61.8% retracement of the reversal impulse.
8. Real structural stop beyond the extreme.
9. Test fixed 2R, 2.5R and 3R separately; do not choose RR from 2026 holdout.
10. Test XAUUSD and GBPUSD separately.

Why it is worth testing: it targets exhaustion after daily-range expansion rather than the already-tested Asia-range geometry.

### B. Asymmetric D1/H4 Trend Pullback

Purpose: revisit continuation only when higher-timeframe regime and trade side justify it.

Candidate logic:
1. D1 and H4 completed-bar structure define bullish, bearish or neutral state.
2. Do not force symmetric long/short behavior.
3. Use pre-2026 data to identify whether a side/session is structurally poor.
4. Require pullback into H1/M15 value after an established daily trend.
5. M15 liquidity sweep inside the pullback.
6. M5 displacement + BOS/MSS.
7. Retracement entry rather than displacement-close entry.
8. Fixed structural stop and 3R external-liquidity target.
9. Separate London and New York variants.

This is not the rejected generic EMA-pullback test: the regime definition and asymmetry are the edge hypothesis.

### C. Compression -> Expansion -> First Pullback

Purpose: capture trend days that the false-break sleeves intentionally avoid.

Candidate logic:
1. Pre-session M15 range/ATR must be in a low historical percentile.
2. London or New York produces genuine displacement through meaningful liquidity.
3. H1/H4 must not oppose the expansion.
4. No breakout chase.
5. Wait for the first 38–61.8% pullback or broken-level retest.
6. Require renewed M5 displacement in the expansion direction.
7. Stop behind the retest invalidation.
8. Target fixed 3R, with enough external runway.

Test separately on XAUUSD and GBPUSD.

### D. Failed Breakout / Second-Entry Fade

Purpose: improve false-break hit quality without simply tightening the existing Asia-fade filter.

Candidate logic:
1. External liquidity sweep/reclaim.
2. First reversal impulse confirms rejection.
3. Market retests the extreme/impulse origin and fails to continue.
4. Second rejection produces local M5 structure shift.
5. Enter only on this second confirmation.
6. Structural stop beyond original extreme.
7. 2.5R–3R target.

The trade count may be lower, so this is a quality sleeve, not the frequency engine.

### E. Volatility-Regime Router

The router is not allowed to invent entries. It only chooses among frozen sleeves:
- directional expansion -> RR10 / compression-expansion;
- exhausted daily range -> DRE fade;
- London false-break regime -> GBPUSD Asia-range fade;
- unclear/mixed state -> WAIT.

Allowed causal regime features:
- daily ATR percentile;
- ADR utilization;
- prior-day range percentile;
- H1/H4 EMA separation normalized by ATR;
- Asia range / ATR;
- realized volatility percentile;
- session and weekday.

All thresholds must be chosen on 2017–2022 and frozen before 2023–2025 validation and 2026 holdout.

## Portfolio risk architecture

Baseline:
- 0.5% risk per trade.
- Prefer one active portfolio trade at a time during research.
- If simultaneous independent positions are later allowed, total hard-stop risk <=1.0%.
- Maximum two realized losses per trading day; then no new entries.
- No recovery sizing after losses.
- Stop opening new risk once the payout target and profitable-day requirement have both been reached.
- Do not depend on 22:00–01:59 UTC low-liquidity profits.

For the USD 2,500 account:
- 0.5% risk = USD 12.50;
- 3R gross winner = about USD 37.50 before costs;
- +8% = USD 200;
- +10% = USD 250.

## Acceptance protocol

Discovery: 2017–2022.
Validation: 2023–2025.
Final holdout: 2026 completed months.

Rank candidates by:
1. number of completed holdout months >= +8%;
2. worst completed holdout month;
3. number of payout-ready months with >=5 qualifying profitable days;
4. floating-DD threshold-event count;
5. 3% daily / 6% static hard-breach count;
6. maximum drawdown;
7. average monthly return.

A candidate fails promotion if the headline return depends on:
- one outsized trade;
- one symbol/direction concentration;
- low-liquidity-window exploitation;
- increasing risk after losses;
- a 2026-specific parameter.

## Immediate next implementation

Build and replay:
1. DRE on XAUUSD and GBPUSD.
2. Compression-expansion-first-pullback on XAUUSD and GBPUSD.
3. Asymmetric D1/H4 pullback on both pairs.
4. Combine only sleeves that are independently positive in both discovery and validation.
5. Run the frozen portfolio on 2026 with Finotive-specific payout and drawdown simulation.

The acceptance target remains +8% minimum per completed month; +10% is the stretch objective.
