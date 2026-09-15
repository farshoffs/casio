# CASIO v2 Strategy — Complete Explanation

This document explains what CASIO v2 is actually doing behind the TradingView dashboard.

Primary implementation:

```text
pine/CASIO_XAUUSD_v2_MTF.pine
```

Operating chart:

```text
XAUUSD M15
Strategy mode: AUTO
```

> CASIO is research software. None of the rules below imply guaranteed profitability.

## 1. Core idea

CASIO is built around one principle:

```text
first decide WHAT market we are in
then decide WHICH playbook is allowed
then decide WHETHER a specific setup is valid
```

It does **not** make H4, H1, M15 and M5 vote equally on every trade.

The decision tree is:

```text
                    XAUUSD
                      |
                REGIME FIRST
                      |
            +---------+---------+
            |                   |
         RANGE?               NOT RANGE
            |                   |
       SCALPING              INTRADAY
            |                   |
      H1 -> M15 -> M5       H4 -> H1 -> M15
            |                   |
            +---------+---------+
                      |
                VETO CHECKS
                      |
                 SCORE / R:R
                      |
               LONG / SHORT / WAIT
```

CASIO is intentionally allowed to output `WAIT` for long periods.

## 2. Why M15 is the operating chart

M15 is the compromise between:

- enough structure to avoid excessive M1/M5 noise,
- enough detail to see liquidity sweeps and structure shifts,
- enough trade frequency for an intraday system,
- practical execution for XAUUSD.

CASIO internally requests H4, H1 and M5 data. You do not have to switch chart timeframe to perform the analysis.

Changing chart timeframe causes TradingView to recalculate the entire strategy, but the v2 trading rules themselves contain an M15 chart guard. Normal use should remain on M15.

## 3. Role of each timeframe

### H4 — directional context

H4 answers:

```text
Should CASIO be structurally interested in LONGS or SHORTS?
```

Current implementation uses:

```text
H4 bullish:
EMA20 > EMA50
AND H4 close > EMA20

H4 bearish:
EMA20 < EMA50
AND H4 close < EMA20
```

If neither is true, H4 is neutral.

This is a trend-context proxy. H4 does not directly trigger an entry.

### H1 — structure, value and liquidity

H1 has several jobs.

#### H1 directional veto

H1 uses the same broad EMA trend logic:

```text
bullish: EMA20 > EMA50 and close > EMA20
bearish: EMA20 < EMA50 and close < EMA20
otherwise neutral
```

For a LONG:

```text
H1 bearish = veto
```

For a SHORT:

```text
H1 bullish = veto
```

A neutral H1 is allowed. This is deliberate: CASIO does not require every timeframe to be perfectly aligned, but it refuses direct higher-timeframe contradiction.

#### H1 value-zone proxy

The current code does **not** yet detect full discretionary supply/demand zones.

Instead it uses a practical value proxy around H1 EMA20, adjusted by H1 ATR, while respecting recent H1 liquidity bounds.

For example, a long wants price to be sufficiently close to the H1 value area rather than chasing far above it.

Default input:

```text
H1 value-zone distance = 0.65 H1 ATR
```

This is one of the areas intended for future research: a true supply/demand model may eventually replace the EMA/ATR proxy if testing proves it better.

#### H1 opposing liquidity

CASIO requests prior H1 20-bar high/low levels.

These are used as practical opposing-liquidity references:

```text
LONG  -> H1 prior high is an upside obstacle/target reference
SHORT -> H1 prior low is a downside obstacle/target reference
```

CASIO will not blindly place a 3R target through a nearer H1 obstacle.

### M15 — main setup and execution

M15 is where the actual Intraday trigger is built.

It evaluates:

- prior 20-bar liquidity highs/lows,
- liquidity sweep/reclaim,
- recent sweep freshness,
- short-term BOS/confirmation,
- ATR,
- ADX,
- 30-bar range condition,
- session eligibility,
- entry, stop and target.

### M5 — Scalping confirmation

M5 is used only as an extra execution confirmation for the range/scalping engine.

Current bullish confirmation:

```text
M5 close > M5 open
AND M5 close > M5 EMA20
```

Bearish is the inverse.

CASIO deliberately does **not** require M5 confirmation for every Intraday trade. Waiting for another lower-timeframe confirmation can produce a later entry and destroy the R:R that made the original M15 setup attractive.

## 4. Regime selection

Before choosing a setup, CASIO asks whether the market qualifies as a range.

### H1 range condition

H1 uses two normalized conditions:

```text
EMA compression / ATR <= 0.40
20-bar H1 range / ATR <= 8.0
```

EMA compression means EMA20 and EMA50 are relatively close compared with current volatility.

### M15 range condition

M15 requires:

```text
ADX <= 22
AND
30-bar range / ATR <= 5.5
```

### AUTO routing

```text
H1 range condition PASS
AND M15 range condition PASS
    -> SCALPING

otherwise
    -> INTRADAY
```

This avoids forcing one strategy into all market conditions.

## 5. Intraday engine

Intraday is designed for directional conditions.

### Long sequence

A simplified long path is:

```text
1. H4 bullish
2. H1 is bullish or neutral, never bearish
3. price is in acceptable H1 value location
4. M15 recently swept sell-side liquidity
5. M15 then confirms bullish structure/BOS
6. current time is London or New York primary window
7. there is >= 1:2.5 usable room to opposing H1 liquidity
8. setup score passes
9. LONG
```

Short is the mirror image.

### Liquidity sweep

For a bullish setup, CASIO watches the previous M15 20-bar low.

Conceptually:

```text
price trades below previous liquidity low
then closes back above it
= sell-side sweep/reclaim
```

For a bearish setup:

```text
price trades above previous liquidity high
then closes back below it
= buy-side sweep/rejection
```

The sweep remains valid for a configurable number of bars, default:

```text
3 M15 bars
```

This allows the BOS to happen shortly after the sweep instead of demanding that everything occur on one candle.

### M15 BOS proxy

Current bullish BOS proxy:

```text
close > previous 5-bar high
AND bullish candle
```

Bearish:

```text
close < previous 5-bar low
AND bearish candle
```

This is a deterministic structure proxy, not a discretionary swing-structure engine.

## 6. Intraday sessions

Default UTC windows:

```text
London:   07:00-11:00 UTC
New York: 12:30-16:30 UTC
```

Intraday entries outside those windows are vetoed.

Reason: the strategy is intended to focus on periods where XAUUSD generally has meaningful participation and movement rather than manufacture entries continuously.

The windows are configurable inputs and should eventually be validated statistically rather than assumed optimal forever.

## 7. Intraday stop loss

For a long, CASIO estimates risk from the swept downside liquidity with an ATR buffer, while enforcing a minimum volatility-based stop distance.

Conceptually:

```text
structural stop near/below swept liquidity
+ small ATR buffer
but never tighter than ~1 M15 ATR
```

Current long calculation uses the previous 20-bar low minus approximately `0.20 * ATR`, with a minimum stop distance of `1.0 * ATR`.

Short is symmetric above prior liquidity.

This attempts to avoid stops that are unrealistically tight relative to XAUUSD volatility.

## 8. Intraday target and R:R veto

Preferred target:

```text
3R
```

But CASIO also checks the opposing H1 liquidity level.

For a LONG:

```text
actual target = nearer of:
- preferred 3R target
- H1 prior 20-bar high
```

For a SHORT:

```text
actual target = nearer of:
- preferred 3R target
- H1 prior 20-bar low
```

Before the trade is even allowed, there must be at least:

```text
1:2.5 usable R:R
```

Default minimum R:R is configurable.

This is important: CASIO does not treat 3R as an entitlement. If market structure only offers 1.4R before a major obstacle, the trade should be `WAIT`, not a forced 3R fantasy target.

## 9. Intraday score

Current long score components are approximately:

| Component | Points |
|---|---:|
| H4 bullish | 20 |
| H1 bullish | 15 |
| H1 neutral | 8 instead of 15 |
| H1 value location | 15 |
| recent sell-side sweep | 20 |
| bullish M15 BOS | 15 |
| primary session | 10 |
| minimum R:R passes | 5 |

Maximum is 100 when H1 is aligned.

Default Intraday minimum score:

```text
80
```

### Important implementation note

Most current score components are also mandatory conditions. Therefore a valid v2 setup will often already have a high score.

So in the current version, the score is better understood as a **quality/status meter**, not a calibrated probability of winning.

A future version can make the score more informative by separating mandatory structure from genuinely optional quality factors.

## 10. Scalping engine

Scalping is only used when AUTO detects a proper range.

It is a mean-reversion system:

```text
range edge -> sweep/reclaim -> lower-timeframe rejection -> target range mean
```

### Long scalp

```text
H1 range regime
+ M15 range regime
+ M15 trades below the range low and closes back above
+ M5 bullish confirmation
+ at least 1:1.3 to range mean
= eligible LONG scalp
```

Short is the inverse from the upper range edge.

### Scalping stop

The stop uses the current M15 excursion plus a small ATR buffer, with a minimum stop distance around:

```text
0.65 M15 ATR
```

### Scalping target

The target is:

```text
M15 30-bar range mean
```

This is deliberately different from Intraday's trend-continuation target.

### Scalping score

Current components:

| Component | Points |
|---|---:|
| H1 range regime | 25 |
| M15 range regime | 20 |
| range-edge sweep | 25 |
| M5 confirmation | 15 |
| minimum R:R passes | 15 |

Maximum: 100.

Default minimum score:

```text
85
```

Again, most components are mandatory, so the current score is descriptive rather than a statistically calibrated win probability.

## 11. Mandatory vetoes are more important than score

CASIO evaluates structural validity before score.

Example:

```text
H4 bullish
H1 bearish
M15 perfect bullish sweep/BOS
```

Result:

```text
WAIT
```

The system does not calculate a compromise such as "72 points, therefore buy". H1 bearish is a hard contradiction for the long.

This is intentional.

## 12. One position at a time

The Pine strategy uses:

```text
pyramiding = 0
```

and only enters when no strategy position is open.

This simplifies research:

- no overlapping signals,
- no averaging into losers,
- no ambiguous attribution of trade performance,
- one initial risk unit per recorded trade.

## 13. R multiples

CASIO evaluates trades in `R`.

If initial risk is the distance from entry to stop:

```text
stop hit       ~= -1R
3R target hit  ~= +3R
1.5R result    ~= +1.5R
```

This makes different price regimes and volatility periods easier to compare than raw dollar movement.

## 14. Rolling audit

CASIO v2 maintains up to 200 closed-trade R results in Pine.

Default current window:

```text
latest 100 closed trades
```

Comparison window:

```text
preceding available 100 trades
```

Metrics include:

- win rate,
- expectancy in R,
- profit factor,
- maximum drawdown in R,
- Intraday win rate,
- Scalping win rate.

Default audit thresholds:

```text
minimum trades before audit: 30
warning win-rate drop:       8 percentage points
warning expectancy drop:     0.20R
critical profit factor:      < 1.0
critical expectancy:         <= 0
```

States:

```text
INSUFFICIENT
HEALTHY
WARNING
CRITICAL
```

The audit does not automatically modify parameters. Automatic self-optimization against the most recent 100 trades would create a serious overfitting risk.

## 15. Why expectancy matters more than win rate

A strategy can be profitable with a moderate win rate if winners are meaningfully larger than losers.

For example, before costs:

```text
42% wins at 3R
expectancy = 0.42*3 - 0.58*1
           = +0.68R/trade
```

A higher-win-rate scalper can still have lower expectancy if its average winner is much smaller.

Therefore CASIO should be judged using:

```text
expectancy
profit factor
max drawdown
trade count
stability
then win rate
```

not win rate alone.

## 16. What the dashboard score is NOT

`Score 90` does **not** mean:

```text
90% probability of winning
```

It means the deterministic setup satisfied a large share of the current quality criteria.

A real probability estimate would require properly calibrated out-of-sample statistical modelling, which CASIO does not currently claim to provide.

## 17. What the current model does NOT yet do

CASIO v2 currently does not claim to have:

- a true discretionary supply/demand-zone detector,
- institutional order-flow data,
- DOM/order-book analysis,
- news sentiment built into the Pine signal,
- spread/slippage modelling identical to a live broker,
- a statistically calibrated probability score,
- automatic profitable self-optimization,
- a 1:1 Python implementation of all v2 MTF rules.

These are important limitations when interpreting backtests.

## 18. TradingView vs Python engine

The Pine v2 strategy is currently the primary live/research implementation of the MTF system.

The Python files under `casio/` predate the full v2 architecture and still represent the earlier deterministic single-timeframe research engine.

Therefore:

```text
TradingView v2 trades
!=
Python backtest trades
```

until v2 is ported to Python.

For current v2 analysis use:

1. TradingView Strategy Tester for the full loaded historical period.
2. The on-chart CASIO rolling audit for recent strategy health.

## 19. How to interpret a live setup

If the dashboard shows something like:

```text
MODE      INTRADAY
H4        BULLISH
H1        BULLISH
SESSION   NEW YORK
SIGNAL    LONG
ENTRY     4xxx.xx
STOP      4xxx.xx
TARGET    4xxx.xx
R:R       2.8
AUDIT     HEALTHY
```

it means:

```text
market regime selected Intraday
-> H4 supported long direction
-> H1 did not veto and price was in acceptable value
-> M15 swept downside liquidity and confirmed structure
-> session filter passed
-> opposing H1 liquidity still allowed required R:R
-> no existing strategy position blocked entry
-> setup was executed in the strategy simulator
```

It does **not** mean the trade is guaranteed to win.

## 20. Current research questions

The most useful next research is not simply adding more indicators. It is testing whether each rule actually improves out-of-sample performance.

Priority questions:

1. Does the H4 veto improve expectancy enough to justify fewer trades?
2. Is the H1 EMA/ATR value proxy better than a true pivot-based supply/demand detector?
3. Are the current London/New York windows optimal for this implementation?
4. Is `sweepFreshBars = 3` better than 1, 2, 4 or 5 out-of-sample?
5. Does M5 confirmation improve Scalping after the worse entry price is considered?
6. Is 1:2.5 the right minimum usable Intraday R:R?
7. Does the Scalping engine add positive expectancy after spread/slippage?
8. Which rules remain stable across multiple years and market regimes?

Parameter changes should be accepted only after adequate sample size and preferably walk-forward/out-of-sample testing.

## 21. Practical operating summary

Normal daily use:

```text
1. Open XAUUSD M15
2. CASIO v2 = AUTO
3. Leave H4/H1/M5 analysis to the script
4. Read MODE / REGIME / biases / SIGNAL
5. WAIT unless a confirmed signal appears
6. Review Entry / Stop / Target / R:R
7. Check current rolling AUDIT status
8. Receive email when confirmed alert fires
```

The strategy is designed around selectivity, not constant activity.
