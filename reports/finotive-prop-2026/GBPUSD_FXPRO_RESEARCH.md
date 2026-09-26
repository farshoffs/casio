# GBPUSD FxPro M1 Research Checkpoint

Data: user-supplied `fxpro_gbpusd_m1.csv`, FxPro M1, 2017-01-01 through 2026-09-24.

## Fixed research rules

- fixed RR 1:3
- real hard stop only
- no BE / protected SL
- no martingale / averaging / recovery sizing
- base risk 0.5% per trade
- MTF filters use completed H1/H4 bars only
- signals generated on M15
- entry on next M1 bar after signal confirmation
- SL/TP replayed on M1
- same-minute SL+TP collision resolves stop-first
- two realized losses/day stops new entries for that day
- 0.04R transaction-cost allowance
- selection logic uses 2017-2022 discovery and 2023-2025 validation; 2026 checked after selection

## Batch 1: continuation / structural families

Tested:
- 0591 impulse -> pullback -> confirmation
- London -> New York continuation
- Asia -> London continuation
- previous-day sweep
- EMA trend pullback
- displacement continuation

Result: no variant had positive expectancy in both 2017-2022 and 2023-2025 with sufficient frequency.

Representative examples:
- 0591 1.0 ATR / age 5: discovery -0.115R/trade, validation -0.070R/trade
- London->NY body 0.4: discovery -0.245R/trade, validation -0.226R/trade
- Asia->London body 0.5: discovery -0.103R/trade, validation -0.108R/trade
- displacement 0.8 ATR: discovery -0.197R/trade, validation -0.180R/trade

Conclusion: reject these continuation variants on GBPUSD.

## Batch 2: reverse / false-break

Blindly flipping the continuation entries did not create a robust edge.

The first robust family was Asia-range false-break fade during London.

Baseline Asia->London false-break fade:
- 2017-2022: 920 trades, 29.89% WR, +0.156R/trade, PF 1.21
- 2023-2025: 453 trades, 26.49% WR, +0.020R/trade, PF 1.03
- 2026 check: 121 trades, 33.06% WR, +0.282R/trade, PF 1.41

2026 monthly return at 0.5% risk:
- Jan +6.40%
- Feb +4.21%
- Mar +2.69%
- Apr -0.28%
- May +3.23%
- Jun +2.69%
- Jul +2.16%
- Aug -4.27%

This is a real candidate edge but fails the required monthly floor.

## Asia-fade conditioning

Best stable pre-2026 quality filter:
- Asia range <= 4 x M15 ATR
- sweep depth <= 0.25 ATR

Pre-2026:
- discovery 154 trades, +0.285R/trade, PF 1.41
- validation 81 trades, +0.293R/trade, PF 1.42

But 2026 frequency collapsed to only 16 trades Jan-Aug, so it cannot support the monthly payout target.

Broader filters retain frequency but still fail the monthly floor. Example Asia range <=5 ATR, sweep <=0.6 ATR:
- discovery +0.115R/trade
- validation +0.146R/trade
- 2026 average month about +1.34%
- August about -3.68%

## Batch 3: New York false-break / exhaustion

London-range false-break during New York can be robust pre-2026 when conditioned on a prior London directional drive.

Best pre-2026 example:
- London drive >=0.5 ATR opposite the fade direction
- sweep depth <=0.3 ATR
- entry before 11:30 NY

Performance:
- 2017-2022: 140 trades, 35.0% WR, +0.360R/trade, PF 1.53
- 2023-2025: 64 trades, 32.81% WR, +0.272R/trade, PF 1.39

But 2026 had only 21 trades and approximately flat average monthly performance, so it is too sparse to solve the payout target.

A broader exhaustion variant (drive >=0.5 ATR, sweep <=0.4 ATR, before 11:30 NY) had a strong 2026 aggregate expectancy (+0.531R/trade) but still produced negative Jan/Feb/Mar/Jul and no month >=5%.

## Other rejected families

- London opening-range fakeout
- New York opening-range fakeout
- previous-week high/low sweep

These did not show sufficiently robust positive expectancy across both pre-2026 eras.

## Current conclusion

GBPUSD does contain robust false-break / mean-reversion edges, but the validated versions do not currently produce enough independent high-quality trades to satisfy a hard +5% monthly floor at 0.5% risk and 3R.

The research should continue with genuinely different families rather than more tuning of Asia/London false-break:
1. daily-range extension mean reversion,
2. weekly/daily trend + intraday pullback with asymmetric session filter,
3. volatility-regime router learned only from pre-2026 data,
4. then combine only independently validated sleeves.

No GBPUSD strategy is accepted yet.
