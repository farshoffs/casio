from __future__ import annotations

import numpy as np
import pandas as pd

from .v3_core import _atr


def _confirmed_structure(frame: pd.DataFrame) -> pd.DataFrame:
    """Return causal confirmed swing structure for any OHLC timeframe.

    A 5-bar fractal is only made available after the two bars to its right have
    closed. That makes the structure usable by research/live code without
    peeking into future candles.
    """
    atr = _atr(frame, 14)
    pivot_high = frame.high.shift(2).where(
        frame.high.shift(2).eq(frame.high.rolling(5, min_periods=5).max())
    )
    pivot_low = frame.low.shift(2).where(
        frame.low.shift(2).eq(frame.low.rolling(5, min_periods=5).min())
    )

    n = len(frame)
    last_ph = np.full(n, np.nan)
    prev_ph = np.full(n, np.nan)
    last_pl = np.full(n, np.nan)
    prev_pl = np.full(n, np.nan)
    equal_high = np.full(n, np.nan)
    equal_low = np.full(n, np.nan)
    bias = np.zeros(n, dtype=np.int8)

    current_ph = previous_ph = current_pl = previous_pl = np.nan
    for i in range(n):
        if np.isfinite(pivot_high.iat[i]):
            previous_ph, current_ph = current_ph, float(pivot_high.iat[i])
        if np.isfinite(pivot_low.iat[i]):
            previous_pl, current_pl = current_pl, float(pivot_low.iat[i])

        last_ph[i], prev_ph[i] = current_ph, previous_ph
        last_pl[i], prev_pl[i] = current_pl, previous_pl
        a = float(atr.iat[i]) if np.isfinite(atr.iat[i]) else np.nan

        if np.isfinite(current_ph) and np.isfinite(previous_ph) and np.isfinite(a):
            if abs(current_ph - previous_ph) <= 0.18 * a:
                equal_high[i] = (current_ph + previous_ph) / 2.0
        if np.isfinite(current_pl) and np.isfinite(previous_pl) and np.isfinite(a):
            if abs(current_pl - previous_pl) <= 0.18 * a:
                equal_low[i] = (current_pl + previous_pl) / 2.0

        if all(np.isfinite(v) for v in (current_ph, previous_ph, current_pl, previous_pl)):
            if current_ph > previous_ph and current_pl > previous_pl:
                bias[i] = 1
            elif current_ph < previous_ph and current_pl < previous_pl:
                bias[i] = -1

    return pd.DataFrame(
        {
            "atr": atr,
            "last_ph": last_ph,
            "prev_ph": prev_ph,
            "last_pl": last_pl,
            "prev_pl": prev_pl,
            "equal_high": equal_high,
            "equal_low": equal_low,
            "structure_bias": bias,
        },
        index=frame.index,
    )
