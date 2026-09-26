# GW/MPL reverse engineering — v0.24 timetable + SOP map

## Timetable reconstructed from the user-supplied training video

Clear session cards in the video show these Malaysia-time monitor windows:

| Window | Session | Video behavior |
|---|---|---|
| 10:30–11:15 | Asia | Monitor direction; re-entry/layer if SOP stays aligned; then raise/setup SL to reduce risk. |
| 12:30–13:30 | Asia–UK | Check H1 direction, then M3. If M3 gives the opposite SOP, wait. Enter only when the same-direction SOP returns and the current candle breaks the moving-average line. |
| 13:30–14:00 | Asia–UK | Re-check M3 for aligned SOP; layer only if still valid. |
| 14:45–15:30 | Asia–UK | H1 context first, then M3. Example in video waits until ~15:57 for the candle to break the MA before layering, showing the window is a monitor window rather than a forced-entry deadline. |
| 16:30–17:00 | UK | Risk-control period. Video says no extra layer because a session transition/reversal may occur. Existing position is allowed to run. |
| 17:30–18:30 | Asia session closed | Mostly observe; example market is sideways. No forced entry. |
| 18:45–19:30 | UK–US | H1 direction first, then M3 same-direction SOP; add a small layer after confirmation and raise SL. |
| 20:45–21:30 | US | Monitor H1 then precision-entry TF; wait for SOP before adding position. |
| 22:45–23:15 | US | Final monitor window. If SOP appears, it can be used, but after ~23:15 the video emphasizes reducing risk as the UK session is closed / reversal risk rises. |

Separate Telegram evidence supplied earlier explicitly shows an additional morning entry window:
- 08:50–09:30 MYT: initial entry window.

The 2026-09-11 MPL M5 SELL signal was posted at 10:50 MYT, which falls directly inside the 10:30–11:15 Asia monitor window.

## Timeframe SOP reconstructed from the video

### H1 = directional bias
The video explicitly opens H1 first and assesses whether buyer or seller momentum/volume is dominant. Example:
- buyer volume strong => focus only on BUY;
- do not take an opposite M3 SOP immediately.

### M3 = precision SOP / entry trigger
The tutorial repeatedly drops to M3 after H1 direction is established.
Entry is delayed until:
- M3 SOP agrees with H1 direction;
- current candle breaks the blue moving-average line in that direction.

Direct reverse-engineering evidence identifies the blue line as SMA20(close).

### M5 = signal/execution timeframe
MPL Telegram messages can be published as M5 signals, e.g. the 2026-09-11 SELL:
- Entry zone 4324–4328
- SL 4332
- TP1 4320
- TP2 4316
- TP3 4312

The geometry from the near-SL edge (4328) is:
- SL = +$4 = 1R
- TP1 = -$8 = 2R
- TP2 = -$12 = 3R
- TP3 = -$16 = 4R

So M5 is clearly part of the live signal/execution workflow even though the tutorial's precision confirmation examples are mainly H1 -> M3.

### M15 = higher-timeframe / management context
Other supplied evidence uses M15 direction and MT5 M15 charts. It should be treated as an intermediate trend/management layer, not as a replacement for H1 direction or M3 precision confirmation.

## Working SOP

1. Wait for an active timetable window.
2. Read H1 direction/momentum.
3. Do not trade against H1.
4. Drop to M3 for the precision SOP.
5. Wait for same-direction SOP and a current-candle break of SMA20.
6. Enter or layer.
7. Raise/setup SL after favorable movement to reduce risk.
8. Around session transitions (especially 16:30–18:30 and after ~23:15), avoid aggressive new layering and prioritize risk reduction.

## Important distinction

Phone screenshot time, chart cursor time, Telegram post time, and official monitor-window time are not interchangeable. A screenshot at 11:35 or 16:00 does not by itself prove an official timetable slot. Treat only explicit session cards / timetable text or signal timestamps inside known windows as schedule evidence.
