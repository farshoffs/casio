# CASIO Next-System Research v1

Status: **research only — no production promotion**

Date: 2026-09-22

## Why this research restarted

The BBMA–RR Adaptive Hybrid v1 looked stable while BBMA used a +0.25R protected stop after +0.5R favorable excursion. A 2026 audit showed that many of the reported "wins" were small protected-stop exits rather than genuine target hits.

That management rule has been rejected and removed.

After removing it, the 2026 Hybrid remained profitable only because RR10 contributed most of the positive R; the BBMA leg itself was negative. Therefore BBMA is **not accepted as the base engine** and the Hybrid research is incomplete.

The task now is to find a replacement portfolio architecture that creates real target-based edge rather than manufacturing a high positive-trade rate through tiny locked profits.

## Research objective

The desired system is XAUUSD intraday, causal, reproducible, and suitable for M5 execution with M15/H1/H4 context.

Primary objectives:

- approximately **8 or more completed trades per 30 days**;
- preferably no chronically dead months;
- genuine asymmetric payoff, with **3R baseline** and 3.5R tested where structure supports it;
- no +0.25R / micro-profit protection mechanism used to inflate win rate;
- strong expectancy and profit factor after conservative same-bar handling;
- materially lower drawdown than the failed BBMA / weak-momentum variants;
- stable behavior across calendar years and broker feeds;
- one active portfolio position at a time unless a future test explicitly proves otherwise.

Risk audit:

- report all strategy results in R first;
- also simulate **RM100 / 5% current-equity risk per trade** because that is the operating stress test;
- a candidate that is positive in R but creates catastrophic 5%-risk drawdown is **not acceptable**.

Working promotion gates for research:

- average frequency >= 8 trades / 30d;
- aim for >= 8 trades in most months, and report the minimum month explicitly;
- expectancy >= +0.15R/trade for a high-frequency engine, with higher standards for sparse engines;
- PF >= 1.30 for high-frequency engines; structural quality engines should aim materially higher;
- positive calendar-year slices >= 8/10 when 2017-2026 data is available;
- target maximum yearly 5%-risk drawdown <= 35%; >45% is a rejection zone unless a portfolio combination demonstrably removes it;
- performance must survive a second feed before promotion.

These are acceptance targets, not optimizer targets. Rules must not be tuned solely to hit the headline numbers.

---

## Existing repo evidence

### 1. Structural QUALITY / ROBUST core — good quality, insufficient frequency

Secondary-feed 2024-2025 research already found a useful structural core:

- TREND_PULLBACK -> displacement retracement;
- EXTERNAL_SWEEP -> strict M5 FVG, London only;
- target around 3.5R;
- structural stop;
- no ADX/RSI router.

The strongest versions produced roughly **2.1-2.9 trades/month**, with PF >2 and expectancy around +0.7R to +1.3R in the stronger 2024/2025 slices.

Conclusion: **freeze this quality core; do not loosen it just to manufacture frequency.**

Source:
- `reports/structural-regime-router/VERIFIED_2024_2026_FINDINGS.md`

### 2. DISPLACEMENT_RETRACE — highest-priority unvalidated lead

The existing structural-frequency research replaced mandatory FVG entry with:

1. structural/liquidity router;
2. M5 displacement + local BOS;
3. FVG midpoint retracement when an FVG exists;
4. otherwise 50% displacement-body retracement;
5. structural stop;
6. external-liquidity runway;
7. 3.5R target.

Latest 60-day Dukascopy discovery result:

- 19 trades;
- **9.5 trades / 30d**;
- 42.105% win rate;
- +3.432R average winner;
- -1.041R average loser;
- **+0.843R expectancy**;
- **PF 2.398**;
- max DD 3.120R.

This is the first existing candidate that simultaneously touched the desired frequency and quality band, but the backward validation was never completed.

Conclusion: **highest-priority full-history challenger, not a proven strategy.**

Source:
- `reports/structural-frequency/INITIAL_CURRENT_RESULT.md`
- `casio/structural_frequency_research.py`

### 3. A+ scale-out — management did not solve regime deterioration

The A+ model deteriorated materially on the secondary feed in 2023-2025. Exit-management changes did not restore a durable edge.

Conclusion: the main problem was **setup selection / regime**, not partial-profit management.

Source:
- `reports/secondary-feed-aplus-2005-2025/REPORT.md`

### 4. RR10 — retain as an expansion engine, not the base engine

RR10 has strong periods but pronounced regime dependence. It remains useful as a specialist expansion/momentum engine when its causal gate is favorable, but it should not be treated as an always-on core.

---

## New FxPro 2017-2026 fixed-3R discovery screen

Dataset:

- FxPro XAUUSD M5;
- 2017-01-02 through 2026-09-18;
- M15/H1/H4 context built causally;
- entry after confirmed signal bar;
- fixed 3R target;
- one active trade;
- conservative stop-first resolution when stop and target are both touched;
- no spread/slippage/commission in this first screen;
- 5% current-equity risk used only for the drawdown stress calculation.

These are deliberately simple implementations used to decide what **not** to spend more research time on. They are not production strategies.

| Technique | Trades | Avg / month | Minimum month | WR @3R | Exp R/trade | PF | Positive years | Worst yearly DD @5% | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Tick-volume / displacement momentum breakout | 2,838 | 24.26 | 13 | 27.10% | +0.084R | 1.115 | 7/10 | ~99.6% | Reject standalone; candidate only behind regime gate |
| ADX/DI M15 pullback continuation | 2,777 | 23.74 | 13 | 26.76% | +0.070R | 1.096 | 4/10 | ~96.8% | Reject standalone |
| Volatility-compression expansion breakout | 1,210 | 10.34 | 3 | 28.43% | +0.137R | 1.192 | 6/10 | ~90.9% | Keep as secondary research candidate |
| H1/H4 Donchian trend breakout | 2,862 | 24.46 | 9 | 26.90% | +0.076R | 1.104 | 5/10 | ~94.5% | Reject standalone |
| ADX expansion breakout | 4,389 | 37.51 | 23 | 25.59% | +0.024R | 1.032 | 3/10 | ~97.8% | Reject |
| Local liquidity sweep reversal | 1,430 | 12.22 | 2 | 24.97% | -0.001R | 0.998 | 3/10 | ~90.6% | Reject |
| Bollinger rejection / range mean reversion | 1,955 | 16.71 | 3 | 25.12% | +0.005R | 1.006 | 3/10 | ~94.3% | Reject |
| Previous-day liquidity sweep reversal | 1,353 | 11.56 | 1 | 24.98% | -0.001R | 0.999 | 3/10 | ~95.2% | Reject |
| Simple Asia-range breakout continuation | 936 | 8.00 | 0 | 25.43% | +0.017R | 1.023 | 5/10 | ~88.2% | Reject simple form |

### Interpretation

Frequency is easy to manufacture. Robust edge is not.

The simple momentum/breakout candidates can exceed 8 trades/month, but at 5% risk their losing sequences create catastrophic drawdown. Simple reversal techniques are near break-even before costs.

Therefore the next system must **not** be "another indicator crossover with a 3R target."

---

## Research architecture to pursue

### Candidate A — Structural Displacement Retrace MTF

**Priority: 1**

Purpose: replace BBMA as the base-quality engine.

Proposed stack:

- H4/H1 confirmed structural direction;
- M15 continuation / liquidity context;
- M5 displacement + local BOS;
- enter retracement, not impulse close;
- FVG50 when present, otherwise displacement-body 50%;
- structural stop behind invalidation;
- 3R and 3.5R targets tested separately;
- no profit-lock stop.

Required tests:

1. FxPro 2017-2026 full history.
2. Year-by-year stability.
3. Monthly trade-frequency distribution.
4. 2026 monthly report.
5. OctaFX secondary-feed replay.
6. Cost sensitivity.
7. MFE/MAE and losing-streak analysis.

### Candidate B — Strict-FVG External Sweep

**Priority: 2**

Purpose: complementary range / liquidity engine.

Rules should remain strict:

- PDH/PDL, Asia H/L, confirmed H1/H4 liquidity;
- sweep + reclaim;
- M5 displacement + BOS;
- **real FVG required**;
- retracement entry;
- London preferred unless data proves wider sessions;
- structural stop;
- 3R / 3.5R external-liquidity target.

Reason: secondary-feed work showed that loose body-retracement external sweeps degraded badly; strict FVG materially improved quality.

This engine is expected to be sparse. Its job is diversification and quality, not reaching 8 trades/month by itself.

### Candidate C — Session Expansion Retest v2

**Priority: 3**

Purpose: add frequency without weakening the structural core.

The previous session-expansion implementation was rejected. Redesign it as:

1. define Asia / prior-day / opening-session liquidity;
2. require genuine expansion through the level;
3. do **not** buy/sell the breakout close;
4. wait for retest;
5. require renewed displacement/BOS on M5;
6. use volume/range expansion only as confirmation, not as the entry itself;
7. enter on retracement after confirmation;
8. structural stop;
9. fixed 3R baseline, 3.5R only with external runway.

A naive opening-range breakout is explicitly rejected. Recent external research also warns that simple ORB variants can disappear after realistic costs. The retest/structure requirement is therefore mandatory.

### Candidate D — Regime-Gated Tick-Volume Momentum

**Priority: 4**

Purpose: high-frequency specialist, not a standalone system.

Raw FxPro screen:

- ~24 trades/month;
- minimum month 13;
- +0.084R/trade at 3R;
- PF 1.115;
- unacceptable standalone drawdown.

Research hypothesis:

Use the raw momentum stream as a **shadow engine** and trade it only when:

- H1/H4 regime is directional;
- daily/H4 expansion is not exhausted;
- M15 displacement and tick-volume impulse agree;
- prior N completed shadow trades have positive rolling expectancy;
- optional session state is favorable.

Test rolling windows 16/24/32 without tuning the threshold to individual years.

The objective is to preserve frequency during genuine momentum regimes and shut it off during the long negative sequences that destroy the standalone version.

### Candidate E — Volatility Compression -> Retest Expansion

**Priority: 5**

Purpose: specialist transition engine.

The simple compression breakout was the strongest of the naive new screens (+0.137R/trade, ~10.3 trades/month), but still produced catastrophic 5%-risk drawdown.

Do not trade the breakout close. Redesign:

- identify M15 compression relative to rolling history;
- require expansion / BOS;
- wait for first controlled retracement;
- require H1 direction or structural asymmetry;
- enter retracement;
- ATR/structural invalidation stop;
- 3R target;
- causal shadow-expectancy gate if needed.

---

## Proposed portfolio, not yet approved

The likely end-state is a **regime-adaptive portfolio**, not one universal entry pattern:

| Regime | Candidate engine |
|---|---|
| clean directional pullback | Structural Displacement Retrace |
| external-liquidity reversal | Strict-FVG External Sweep |
| session transition / fresh expansion | Session Expansion Retest v2 |
| strong momentum expansion | RR10 and/or Regime-Gated Tick-Volume Momentum |
| compression -> expansion transition | Compression Retest |
| no clean state | WAIT |

No engine may use year/date as a trading rule.

---

## Test protocol

Because most historical years have already been inspected during prior CASIO research, future results on 2017-2026 must be called **discovery / robustness**, not pristine out-of-sample evidence.

For every candidate:

1. freeze the rule set before looking at detailed yearly P&L;
2. run full FxPro 2017-2026;
3. report each year with RM100 reset, 5% risk;
4. report monthly frequency and minimum month;
5. report WR, expectancy, PF, max DD, max win/loss streak;
6. report exact TP/SL distribution;
7. add 0.02R / 0.05R / 0.10R cost stress;
8. replay unchanged rules on OctaFX secondary data;
9. compare directional and session asymmetry;
10. reject candidates that require special year-specific rules.

Portfolio tests come **after** individual-engine tests.

---

## External research notes

The system search is aligned with broader evidence but does not assume that published results transfer directly to XAUUSD M5:

- Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*, documents return persistence across many futures markets.
- Kim, Tse & Wald (2016) shows that volatility scaling explains an important part of reported time-series momentum performance, so risk normalization must be separated from entry edge.
- Opening-range breakout evidence is mixed. Some older futures work reports intraday trending effects, while a 2026 pre-registered futures study reports that simple ORB variants fail after realistic costs. Therefore CASIO should test structured retest entries rather than naive breakout-close entries.

---

## Current decision

**Do not restore the +0.25R BBMA profit lock.**

**Do not promote BBMA as the base engine.**

The next full-history run should start with:

1. Structural Displacement Retrace MTF;
2. Strict-FVG External Sweep;
3. Session Expansion Retest v2;
4. Regime-Gated Tick-Volume Momentum;
5. Compression Retest.

RR10 remains available as the existing specialist expansion engine while these challengers are tested.

No candidate is considered to have fulfilled the target until the frozen rules pass the full protocol above.
