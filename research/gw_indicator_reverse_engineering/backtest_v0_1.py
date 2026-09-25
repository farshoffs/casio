#!/usr/bin/env python3
import numpy as np
import pandas as pd
from datetime import time

CSV = "fxpro_xauusd_m1.csv"
START_EQUITY = 100.0
RISK_PCT = 0.05
SL_DIST = 4.0
RR = 3.0
RMA_LEN = 10

ENTRY_WINDOWS_MYT = [
    ("W1", time(8, 50), time(9, 30)),
    ("W2", time(10, 30), time(11, 15)),
    ("W3", time(13, 30), time(14, 30)),
]

def resample_ohlc(d, rule):
    return d.resample(rule, label="left", closed="left", origin="epoch").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    ).dropna()

def rma(s, n=10):
    return s.ewm(alpha=1/n, adjust=False).mean()

def assign_window(ts_utc):
    local = ts_utc.tz_convert("Asia/Kuala_Lumpur")
    tt = local.time()
    for name, a, b in ENTRY_WINDOWS_MYT:
        if a <= tt <= b:
            return name
    return None

df = pd.read_csv(CSV, parse_dates=["time_utc"])
df = df[df["time_utc"].dt.year == 2026].set_index("time_utc").sort_index()
m1 = df[["open", "high", "low", "close", "tick_volume"]]
m3 = resample_ohlc(m1, "3min")
m15 = resample_ohlc(m1, "15min")
h1 = resample_ohlc(m1, "1h")

sig = m3[["open", "high", "low", "close"]].copy()
sig["m3_ma"] = rma(m3.close, RMA_LEN)
sig["m3_prev_close"] = m3.close.shift(1)
sig["m3_prev_ma"] = sig["m3_ma"].shift(1)

for name, htf, rule in [("m15", m15, "15min"), ("h1", h1, "1h")]:
    full_ma = rma(htf.close, RMA_LEN)
    prev_ma = full_ma.shift(1)
    periods = sig.index.floor(rule)
    pm = prev_ma.reindex(periods).to_numpy()
    op = htf.open.reindex(periods).to_numpy()
    sig[f"{name}_open"] = op
    sig[f"{name}_ma"] = 0.1 * sig["close"].to_numpy() + 0.9 * pm

sig["buy_align"] = (
    (sig.close > sig.open) & (sig.close > sig.m3_ma) &
    (sig.close > sig.m15_open) & (sig.close > sig.m15_ma) &
    (sig.close > sig.h1_open) & (sig.close > sig.h1_ma)
)
sig["sell_align"] = (
    (sig.close < sig.open) & (sig.close < sig.m3_ma) &
    (sig.close < sig.m15_open) & (sig.close < sig.m15_ma) &
    (sig.close < sig.h1_open) & (sig.close < sig.h1_ma)
)
sig["buy_fresh"] = sig.buy_align & (sig.m3_prev_close <= sig.m3_prev_ma)
sig["sell_fresh"] = sig.sell_align & (sig.m3_prev_close >= sig.m3_prev_ma)
sig["buy_dist"] = sig.close - sig.m15_ma
sig["sell_dist"] = sig.m15_ma - sig.close
sig["entry_time"] = sig.index + pd.Timedelta(minutes=3)
sig = sig.dropna()

m1idx = m1.index
ns = m1idx.view("int64")
o = m1.open.to_numpy()
h = m1.high.to_numpy()
l = m1.low.to_numpy()

def pos(ts):
    return int(np.searchsorted(ns, pd.Timestamp(ts).value, side="left"))

def run(name, buy_mask, sell_mask, allow_reentry=True):
    trades = []
    busy_until = -1
    used = set()
    for i in np.flatnonzero((buy_mask | sell_mask).to_numpy()):
        row = sig.iloc[i]
        et = row.entry_time
        w = assign_window(et)
        if w is None:
            continue
        key = (et.tz_convert("Asia/Kuala_Lumpur").date(), w)
        if not allow_reentry and key in used:
            continue
        ep = pos(et)
        if ep >= len(m1idx) or ep <= busy_until:
            continue
        if m1idx[ep] > et + pd.Timedelta(minutes=2):
            continue
        side = "buy" if bool(buy_mask.iloc[i]) else "sell"
        entry = float(o[ep])
        sl = entry - SL_DIST if side == "buy" else entry + SL_DIST
        tp = entry + SL_DIST * RR if side == "buy" else entry - SL_DIST * RR
        out = None
        for j in range(ep, len(m1idx)):
            if side == "buy":
                hs, ht = l[j] <= sl, h[j] >= tp
            else:
                hs, ht = h[j] >= sl, l[j] <= tp
            if hs and ht:
                out, ex = "L", j
                break
            if hs:
                out, ex = "L", j
                break
            if ht:
                out, ex = "W", j
                break
        if out is None:
            break
        busy_until = ex
        used.add(key)
        trades.append((m1idx[ep], out, RR if out == "W" else -1.0))

    eq = START_EQUITY
    peak = eq
    maxdd = 0.0
    for _, out, _ in trades:
        eq *= (1 + RISK_PCT * RR) if out == "W" else (1 - RISK_PCT)
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak)
    wins = sum(x[1] == "W" for x in trades)
    print({
        "name": name,
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "wr": wins / len(trades) if trades else 0,
        "netR": sum(x[2] for x in trades),
        "end_equity": eq,
        "maxdd": maxdd,
    })

zone2_buy = sig.buy_align & sig.buy_dist.between(0, 2)
zone2_sell = sig.sell_align & sig.sell_dist.between(0, 2)

run(
    "Candidate A: zone<=2 + fresh M3",
    zone2_buy & sig.buy_fresh,
    zone2_sell & sig.sell_fresh,
    allow_reentry=True,
)
run(
    "Candidate B: zone<=2 + MTF align",
    zone2_buy,
    zone2_sell,
    allow_reentry=True,
)
