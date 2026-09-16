# CASIO Structural Portfolio — Latest-First Findings

Status: **research only**. The existing live v3 engine is not replaced by this report.

## Research objective

Find the combination of three structural XAUUSD playbooks that reaches, without curve fitting:

- ~8 completed trades / 30 days
- 42–50% win rate
- ~3.5R average winner
- average loss ~1R or better
- >= +0.70R expectancy / trade
- PF >= 2.0

Research order is deliberately **latest first, then backward**. We do not restart strategy development from 2020 merely because that is the oldest canonical data currently in GitHub.

## Model being researched

No ADX or RSI is used.

### A — Trend pullback continuation

- Confirmed D1/H4/H1 swing structure provides direction.
- M15 structure must not oppose the trade.
- M5 first takes internal liquidity.
- M5 then produces displacement + local BOS and a fair-value gap.
- Entry is the 50% FVG retracement, not the impulse close.
- Continuation entry must agree with the current daily auction relative to the daily open.
- Stop sits behind recent M5 structure with a small volatility buffer.
- External liquidity must provide at least 3.5R of room.

### B — External liquidity sweep

- Liquidity universe: PDH/PDL, Asia H/L, confirmed H1/H4 swings and prior-week H/L.
- Sweep/reclaim must be followed by M5 displacement + BOS + FVG.
- Entry is the FVG midpoint retracement.
- A price-action regime router avoids exhausted daily expansion and very compressed H4 conditions.
- Stop is structural; target baseline is 3.5R.

### C — Session expansion retest

- London/NY breaks meaningful Asia or previous-day liquidity.
- No chase entry.
- Wait for a retest, then renewed M5 displacement/BOS/FVG.
- Entry is on retracement after confirmation.
- Target must have >=3.5R external runway.

## Latest-first evidence collected so far

### Recent 1–15 Sep 2026 sample

The uploaded current BID sample is too short to initialize the full 20-day structural regime router, so it is treated as a current-market sanity sample rather than an optimization sample. A looser structural/FVG diagnostic produced only two filled trades: one -1.04R stop and one +3.43R winner. That is 50% WR, about +1.20R expectancy and PF ~3.31, but **N=2 is not evidence of a durable edge**.

### 2025 — latest complete secondary-feed year

The current quality-router prototype produced:

- 44 completed trades
- 3.62 trades / 30 days
- 45.45% WR
- +3.25R average winner
- -1.08R average loss
- +0.890R expectancy / trade
- PF 2.51
- max drawdown 5.26R

This clears the quality objectives for WR / expectancy / PF, but **does not yet reach the required frequency** and average winner is still a little below the ~3.5R objective.

### 2024

Same rules, frozen:

- 48 trades
- 3.93 trades / 30 days
- 31.25% WR
- +2.52R average winner
- +0.057R expectancy
- PF 1.08

Positive but weak. This means 2025 performance is not sufficient to promote the model.

### 2023

Same rules, frozen:

- 35 trades
- 2.88 trades / 30 days
- 31.43% WR
- +3.01R average winner
- +0.190R expectancy
- PF 1.25

Again positive, but below the target portfolio quality.

### 2022

The same rules fail:

- 52 trades
- 4.27 trades / 30 days
- 19.23% WR
- -0.387R expectancy
- PF 0.55

This is the useful failure. It proves the current router still does not identify every structural regime correctly.

## What the research has established

1. FVG/retracement execution materially improves entry asymmetry versus buying/selling the displacement close.
2. Trend-pullback winners tend to preserve ~3.4R payoff, but setup selection must improve.
3. External-sweep setups are currently the strongest frequency contributor in the latest regime.
4. Pure exit-management changes are not enough; the edge is primarily in market-state and setup selection.
5. The immediate research problem is **not more indicators**. It is to add complementary structural playbooks/regime routing until frequency approaches ~8/month without destroying the 2025 quality profile.

## Promotion rule

The model is not promoted because one year looks good. A challenger must maintain the target profile across the latest market first, then survive earlier chronological windows and a different feed. The TradingView assistant may expose the research state visually, but live automation stays on the existing production engine until the structural portfolio clears that bar.
