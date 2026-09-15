from dataclasses import dataclass


@dataclass(frozen=True)
class IntradayConfig:
    min_score: int = 70
    target_rr: float = 3.0
    atr_period: int = 14
    fast_ema: int = 20
    slow_ema: int = 50
    sweep_lookback: int = 20
    structure_lookback: int = 10
    max_atr_pct: float = 0.012


@dataclass(frozen=True)
class ScalpingConfig:
    min_score: int = 68
    target_rr: float = 1.5
    atr_period: int = 14
    range_lookback: int = 30
    adx_period: int = 14
    max_adx: float = 22.0
    max_range_atr: float = 5.5
    edge_fraction: float = 0.22


@dataclass(frozen=True)
class AuditConfig:
    rolling_trades: int = 100
    min_trades_for_audit: int = 30
    warn_win_rate_drop_pct: float = 8.0
    warn_expectancy_drop_r: float = 0.20
    critical_profit_factor: float = 1.0
    critical_expectancy_r: float = 0.0
