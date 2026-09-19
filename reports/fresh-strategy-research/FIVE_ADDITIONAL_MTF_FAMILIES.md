# Fresh XAUUSD Strategy Research — Five Additional MTF Families

## Scope

This branch is a clean strategy-discovery branch. RR10/0591/router logic is not reused.

Data:
- FxPro XAUUSD M5: 687,746 bars, 2017-01-02 -> 2026-09-18
- FxPro XAUUSD M15: 229,303 bars, 2017-01-02 -> 2026-09-18
- H1/H4 context is resampled from the supplied FxPro history using completed bars only
- scoring starts 2017-03-04 after warm-up

Research constraints:
- RM100 starting equity, reset every calendar year
- 5% current-equity risk per trade
- one active trade
- stop-first treatment if SL and TP collide on one M5 bar
- genuine M5 execution
- structural M5 stops
- gross results before spread/commission/slippage
- desired minimum frequency: >=8 trades per completed month

This iteration deliberately broadens beyond:
- supply/demand retests
- FVG continuation/reversal
- liquidity sweeps
- session/range-expansion setups

## Five new strategy families

### 1. MTF EMA Pullback Reclaim

Concept:
- H1 directional EMA trend
- optional H4 directional agreement
- completed M15 remains on the trend side of EMA20
- M5 pulls through EMA20 and closes back through it in the HTF direction
- structural stop beyond recent M5 swing

Best simple screen:
- H4 agreement required
- 2R target

Result:
- 6,847 trades
- 34.82% WR
- +0.045R expectancy
- PF 1.07
- ~59.6 trades/month
- minimum completed-month count: 33
- 6/10 calendar years finish above RM100
- worst annual max DD: ~99.3%

Verdict:
- frequency is far more than sufficient
- raw edge is too weak and risk sequencing is unacceptable
- keep only as a possible component, not a standalone strategy

### 2. HTF Range-Regime RSI Mean Reversion

Concept:
- completed H1 ADX identifies non-trending regime
- M15 RSI5 reaches an extreme
- M5 RSI/EMA turn confirms the reversal
- stop beyond recent M5 swing

Best simple screen:
- H1 ADX <20
- M15 RSI5 <15 / >85
- 1.5R target

Result:
- 223 trades
- 40.36% WR
- +0.009R expectancy
- PF 1.02
- ~2.0 trades/month
- minimum month: 0
- 4/10 profitable calendar years

Verdict:
- insufficient frequency
- no meaningful robust edge
- reject as a primary strategy

### 3. Tick-Volume Momentum Continuation

Concept:
- H1 directional EMA trend
- M5 tick-volume z-score impulse
- strong M5 displacement body
- M5 local breakout in the HTF direction
- stop beyond the impulse candle
- no RR10/FVG logic used

Best frequency-qualified screen:
- M5 volume z-score >=2.0
- H1 trend
- 2.5R target

Result:
- 2,784 trades
- 30.60% WR
- +0.071R expectancy
- PF 1.10
- ~24.3 trades/month
- minimum completed-month count: 10
- >=8 trades in 100% of completed months
- 7/10 calendar years finish above RM100
- worst annual max DD: ~94.9%

Verdict:
- passes frequency cleanly
- promising as a raw signal generator
- standalone risk sequencing is still unacceptable
- keep for second-stage research

### 4. Exhaustion Snapback Reversal

Concept:
- three completed M15 bars form an outsized directional move relative to M15 ATR
- M15 RSI reaches an extreme
- H1 is not in an excessively strong trend
- M5 crosses back through EMA9 in the reversal direction
- stop beyond recent M5 swing

Highest-expectancy simple screen:
- 3-bar move >=2.0 M15 ATR
- H1 ADX <22
- 2.5R target

Result:
- 203 trades
- 33.00% WR
- +0.155R expectancy
- PF 1.23
- ~1.8 trades/month
- minimum month: 0
- 4/10 profitable calendar years

Verdict:
- interesting per-trade payoff
- far below the required frequency
- useful only as a secondary/portfolio strategy, not the user's primary strategy

### 5. MTF ADX/DI Momentum Rotation

Concept:
- H1 EMA trend + ADX trend-strength regime
- +DI/-DI confirms direction
- H4 EMA direction agrees
- M5 EMA9 crosses EMA20 back into the HTF direction
- avoids extreme M15 RSI
- stop beyond recent M5 swing

Frequency-qualified screen:
- H1 ADX >=22
- H4 trend agreement
- 2R target

Result:
- 2,456 trades
- 35.63% WR
- +0.069R expectancy
- PF 1.11
- ~21.3 trades/month
- minimum completed-month count: 10
- >=8 trades in 100% of completed months
- 6/10 calendar years finish above RM100
- worst annual max DD: ~88.0%

Verdict:
- passes the frequency requirement cleanly
- better raw stability than the very-high-frequency pullback family
- still not robust enough as a standalone system
- keep for second-stage research

## Initial ranking

The five families were screened for both edge and the user's frequency requirement.

### Keep for deeper research
1. **Tick-Volume Momentum Continuation**
   - clean frequency
   - 2.5R
   - positive aggregate expectancy
   - 7/10 profitable years

2. **MTF ADX/DI Momentum Rotation**
   - clean frequency
   - 2R
   - positive aggregate expectancy
   - 6/10 profitable years

3. **MTF EMA Pullback Reclaim**
   - abundant frequency
   - weak but positive aggregate edge
   - may be useful after stronger quality controls

### Secondary / portfolio-only
4. **Exhaustion Snapback**
   - attractive per-trade expectancy
   - far too infrequent as a primary system

### Reject as primary
5. **HTF RSI Mean Reversion**
   - frequency and robustness both fail

## Important conclusion

None of these five should be called the final new strategy yet.

Two families pass the >=8-trades-per-month constraint in every completed month:
- Tick-Volume Momentum Continuation
- ADX/DI Momentum Rotation

But both still have unacceptable annual drawdown under raw 5%-risk standalone replay.

The next research should not over-optimize their indicators. The better next step is to test whether:
- a clean H4/D1 regime condition
- a session-independent volatility normalization
- or a portfolio combination of genuinely different strategy families

can improve annual robustness while preserving the frequency floor.

No RR10 code or live strategy was changed.
