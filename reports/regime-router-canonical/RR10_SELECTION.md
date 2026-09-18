# CASIO RR10 — Canonical Regime Router

RR10 is the single live Regime Router ruleset. The previous five names remain only as internal confirmation features; they are not independent live engines.

## Frozen selection

- Base setup: M15 0591 impulse -> pullback -> confirmation.
- Router context: use the old router's 0591-selected stream.
- Session gate: only outside 07:00-12:00 UTC and 12:30-17:00 UTC.
- Higher-timeframe gate: at least one of completed H1/H4 biases aligns with the signal.
- Strong-trend mode: 0591 direction must match the H1/H4 trend.
- Mixed mode: no same-bar structural-portfolio priority signal and at least two same-direction confirmations in the prior two M15 bars.
- Entry: confirmed M15 close.
- Stop: 0591 pullback extreme plus/minus 0.12 impulse ATR.
- Target: fixed 3R.
- Lifecycle: one active trade only; Entry/SL/TP are frozen until SL or TP. Later signals do not replace it.
- Research sizing: RM100 initial balance, 5% of current equity risked per closed trade.

## FxPro M15 verification

| Period | Closed trades | Trades / 30d | Win rate | Expectancy | PF | RM100 -> | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024 | 77 | 6.31 | 35.06% | +0.403R | 1.62 | RM334.98 | 35.50% |
| 2025 | 95 | 7.81 | 44.21% | +0.768R | 2.38 | RM2,337.01 | 27.52% |
| 2026 YTD to 18 Sep | 69 | 7.96 | 43.48% | +0.739R | 2.31 | RM895.69 | 22.62% |

The requested 70% win-rate goal was explicitly searched across RR 3-6 and causal router/filter variants. No configuration near the required trade frequency produced a verified 70% hit rate. RR10 uses 3R because it gives the highest hit rate and the closest match to ~8 trades/month among the robust profitable candidates. The 70% figure remains a future acceptance target, not a claimed backtest result.

No year/date is used as a trading rule.
