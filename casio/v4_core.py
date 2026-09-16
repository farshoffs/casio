from __future__ import annotations

from dataclasses import dataclass

from .v3_core import load_m5_csv, prepare_features


@dataclass(frozen=True)
class V4Config:
    """CASIO v4 experimental setup-first configuration.

    v4 deliberately keeps v3's causal MTF feature pipeline, but changes decision
    architecture: three independent M15 setup detectors compete on quality score.
    Higher-timeframe context mostly scores a setup instead of vetoing it.
    """

    # Playbook switches make clean ablations possible without changing logic.
    enable_trend_pullback: bool = True
    enable_range_rotation: bool = True
    enable_breakout_retest: bool = True

    # Global execution / research
    min_score: int = 68
    round_trip_cost_bps: float = 1.0
    abnormal_candle_atr: float = 2.5

    # Trend pullback
    trend_target_rr: float = 2.2
    trend_min_rr: float = 1.6
    trend_pullback_atr: float = 0.30
    trend_min_score: int = 70
    trend_min_adx: float = 18.0
    trend_require_m5: bool = True

    # Range rotation
    range_target: str = "mean"
    range_edge_fraction: float = 0.25
    range_min_rr: float = 1.30
    range_min_score: int = 68
    range_h1_compression_atr: float = 0.65
    range_h1_max_range_atr: float = 9.0
    range_m15_max_adx: float = 24.0
    range_m15_max_range_atr: float = 6.5
    range_require_m5: bool = True
    range_require_edge_reclaim: bool = True

    # Breakout -> retest continuation
    breakout_target_rr: float = 2.4
    breakout_min_rr: float = 1.7
    breakout_min_score: int = 72
    breakout_expansion_atr: float = 1.20
    breakout_retest_atr: float = 0.20
    breakout_retest_min_bars: int = 1
    breakout_retest_max_bars: int = 5
    breakout_pre_max_adx: float = 24.0
    breakout_pre_max_range_atr: float = 5.5
    breakout_require_m5: bool = True

    # Context / quality
    session_bonus_primary: int = 5
    session_bonus_asia: int = 2
    htf_alignment_bonus: int = 10
    htf_neutral_bonus: int = 4
    sweep_bonus: int = 8
    bos_bonus: int = 8
    m5_bonus: int = 8
    rr_bonus: int = 8
    strong_conflict_veto: bool = True

    # Sessions are context only in v4, not hard gates.
    asia_start: str = "00:00"
    asia_end: str = "06:00"
    london_start: str = "07:00"
    london_end: str = "11:00"
    new_york_start: str = "12:30"
    new_york_end: str = "16:30"


__all__ = ["V4Config", "load_m5_csv", "prepare_features"]
