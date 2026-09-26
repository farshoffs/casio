# CASIO Prop System V1

Status: **system candidate on `research/finotive-prop`**. This document is intentionally system-level. Individual research techniques are implementation details, not the product.

## Objective

Account: Finotive Instant Funding Lite USD 2,500.

System target:
- at least +5% realized return per completed calendar month,
- at least 5 Minimum Profitable Days,
- no 3% daily drawdown hard breach,
- no 6% static maximum-drawdown hard breach,
- avoid repeated 1.5% floating-drawdown events,
- no martingale, grid, averaging losers, recovery sizing or protected/virtual-stop accounting.

## System interface

The system has only three outputs:

- `TRADE`
- `WAIT`
- `HALT`

It does not expose a list of strategies to the operator.

## Architecture

### 1. Candidate layer

Validated internal engines may emit candidate trades. Candidates are not orders.

Every candidate must contain:
- symbol,
- direction,
- entry,
- real stop,
- target,
- timestamp,
- engine identity,
- pre-2026 validation state.

### 2. Causal portfolio router

`casio/casio_prop_system.py` ranks simultaneous candidates using only results that were already closed before the new signal.

Rolling health window: 120 days.

A sleeve remains eligible only when its rolling history has:
- minimum 5 closed trades,
- expectancy >= +0.05R,
- PF >= 1.05.

A pre-2026-validated sleeve can bootstrap the live router from its frozen prior expectancy. Once enough current results exist, the rolling causal score takes over.

Only the highest-ranked candidate is taken when signals overlap.

### 3. Position concurrency

Default: one active portfolio position.

This deliberately avoids:
- duplicated correlated XAU exposure,
- stacking several versions of the same idea,
- accidental floating-drawdown concentration.

### 4. Risk governor

Normal risk: **0.50% equity per trade**.

Monthly protection:
- month <= -2.0%: reduce to 0.35%,
- month <= -3.5%: reduce to 0.25%,
- internal static-DD brake at -4.5%, before the 6% hard limit.

Daily protection:
- maximum 2 realized losses in one Finotive trading day,
- internal daily brake at -1.75%, before the 3% hard limit.

Planned risk on one symbol may not exceed 0.75%.

No increase in risk after losses.

### 5. Profit governor

Once both are true:
- realized month return >= +5%,
- MPD count >= 5,

the system stops opening new risk for that month.

The target is therefore a stopping condition, not a reason to force extra trades.

## Verified 2026 opportunity envelope

The audited FxPro pair-neutral checkpoint tested XAUUSD, GBPUSD, GBPJPY and EURUSD with real stops and <=0.5% risk.

The deliberately impossible oracle screen produced:

| Month | Oracle upper bound |
|---|---:|
| Jan 2026 | +15.85% |
| Feb 2026 | +3.36% |
| Mar 2026 | +5.38% |
| Apr 2026 | +3.87% |
| May 2026 | +7.12% |
| Jun 2026 | +15.71% |
| Jul 2026 | +2.92% |
| Aug 2026 | +8.34% |

All eight months were positive.

Total across the eight monthly figures is +62.55 percentage points, an arithmetic monthly average of **+7.82%**.

Worst month: **+2.92%**.

Important: this is an upper bound, not a tradable backtest. It proves the current candidate universe contained profitable opportunity in every completed 2026 month, but it does not prove a causal router can select it.

## System-level conclusion

The old candidate universe is sufficient to make every completed 2026 month positive under the oracle screen, but is **not sufficient to prove a causal +5% monthly floor at 0.5% risk**.

The gap to +5% in the three oracle-under-floor months is:

- February: +1.64 percentage points,
- April: +1.13 percentage points,
- July: +2.08 percentage points.

Therefore CASIO Prop System V1 is built around:

1. causal selection among validated candidate streams,
2. strict portfolio-level risk governance,
3. automatic WAIT/HALT states,
4. addition of genuinely independent candidate sources only when they improve the system-level monthly floor.

No candidate is promoted merely because it raises average return.

## Promotion test

A system build is deployable only when the final causal replay—not the oracle—meets all of these on completed holdout months:

1. every month >= +5%,
2. >=5 MPD,
3. zero daily hard breaches,
4. zero static hard breaches,
5. no repeated floating-DD abuse,
6. one active portfolio position by default,
7. no current-month information used to select that month's engine.

Until then the code remains on the research branch and the production strategy is unchanged.
