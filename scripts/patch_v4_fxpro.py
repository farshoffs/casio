from pathlib import Path

p = Path("pine/CASIO_XAUUSD_v4_CONFLUENCE.pine")
s = p.read_text()

s = s.replace('profile = input.string("FREQUENCY", "Profile"', 'profile = input.string("QUALITY_70", "Profile"')
s = s.replace('maxTradesPerDay = input.int(3, "Maximum accepted trades / day"', 'maxTradesPerDay = input.int(2, "Maximum accepted trades / day"')
s = s.replace('cooldownBars = input.int(6, "Cooldown M5 bars"', 'cooldownBars = input.int(9, "Cooldown M5 bars"')
if 'maxTradesPerWeek = input.int' not in s:
    s = s.replace(
        'weeklyTarget = input.int(8, "Weekly trade target", minval=1, maxval=25, group=groupProfile)\n',
        'weeklyTarget = input.int(8, "Weekly trade target", minval=1, maxval=25, group=groupProfile)\n'
        'maxTradesPerWeek = input.int(10, "Maximum accepted trades / week", minval=5, maxval=25, group=groupProfile)\n'
    )
s = s.replace('tradeAsia = input.bool(true, "Allow high-score Asia setups"', 'tradeAsia = input.bool(false, "Allow high-score Asia setups"')

start = s.index('// Confirmed higher-timeframe context — previous CLOSED bar only.')
end = s.index('h4Bias =', start)
new_htf = '''// Confirmed higher-timeframe context with lookahead OFF.
// Raw HTF values may update during the current HTF bar, so we only snapshot
// the value from the final M5 bar of the HTF period when the next period begins.
f_htf_raw_bundle() =>
    ema20_ = ta.ema(close, 20)
    ema50_ = ta.ema(close, 50)
    atr_ = ta.atr(14)
    [close, ema20_, ema50_, atr_]

f_m15_raw_bundle() =>
    ema20_ = ta.ema(close, 20)
    ema50_ = ta.ema(close, 50)
    atr_ = ta.atr(14)
    [plus_, minus_, adx_] = ta.dmi(14, 14)
    [close, ema20_, ema50_, atr_, adx_]

[h4CloseRaw, h4Ema20Raw, h4Ema50Raw, h4AtrRaw] = request.security(syminfo.tickerid, "240", f_htf_raw_bundle(), lookahead=barmerge.lookahead_off, calc_bars_count=2500)
[h1CloseRaw, h1Ema20Raw, h1Ema50Raw, h1AtrRaw] = request.security(syminfo.tickerid, "60", f_htf_raw_bundle(), lookahead=barmerge.lookahead_off, calc_bars_count=5000)
[m15CloseRaw, m15Ema20Raw, m15Ema50Raw, m15AtrRaw, m15AdxRaw] = request.security(syminfo.tickerid, "15", f_m15_raw_bundle(), lookahead=barmerge.lookahead_off, calc_bars_count=10000)

newH4 = ta.change(time("240")) != 0
newH1 = ta.change(time("60")) != 0
newM15 = ta.change(time("15")) != 0

h4Close = ta.valuewhen(newH4, h4CloseRaw[1], 0)
h4Ema20 = ta.valuewhen(newH4, h4Ema20Raw[1], 0)
h4Ema50 = ta.valuewhen(newH4, h4Ema50Raw[1], 0)
h4Atr = ta.valuewhen(newH4, h4AtrRaw[1], 0)
h1Close = ta.valuewhen(newH1, h1CloseRaw[1], 0)
h1Ema20 = ta.valuewhen(newH1, h1Ema20Raw[1], 0)
h1Ema50 = ta.valuewhen(newH1, h1Ema50Raw[1], 0)
h1Atr = ta.valuewhen(newH1, h1AtrRaw[1], 0)
m15Close = ta.valuewhen(newM15, m15CloseRaw[1], 0)
m15Ema20 = ta.valuewhen(newM15, m15Ema20Raw[1], 0)
m15Ema50 = ta.valuewhen(newM15, m15Ema50Raw[1], 0)
m15Atr = ta.valuewhen(newM15, m15AtrRaw[1], 0)
m15Adx = ta.valuewhen(newM15, m15AdxRaw[1], 0)

'''
s = s[:start] + new_htf + s[end:]

old_daily = '''prevDayHigh = request.security(syminfo.tickerid, "D", high[1], lookahead=barmerge.lookahead_on)
prevDayLow = request.security(syminfo.tickerid, "D", low[1], lookahead=barmerge.lookahead_on)

newDay = ta.change(time("D")) != 0
'''
new_daily = '''newDay = ta.change(time("D")) != 0
dayHighRaw = request.security(syminfo.tickerid, "D", high, lookahead=barmerge.lookahead_off)
dayLowRaw = request.security(syminfo.tickerid, "D", low, lookahead=barmerge.lookahead_off)
prevDayHigh = ta.valuewhen(newDay, dayHighRaw[1], 0)
prevDayLow = ta.valuewhen(newDay, dayLowRaw[1], 0)

'''
if old_daily not in s:
    raise SystemExit("daily block not found")
s = s.replace(old_daily, new_daily)

old_consider = 'canConsider = chartIsM5 and barstate.isconfirmed and inBacktestWindow and sessionAllowed and flat and cooldownReady and dayTrades < maxTradesPerDay'
new_consider = 'qualityRegimeOk = profile != "QUALITY_70" or directionalRegime\ncanConsider = chartIsM5 and barstate.isconfirmed and inBacktestWindow and sessionAllowed and flat and cooldownReady and dayTrades < maxTradesPerDay and weekTrades < maxTradesPerWeek and qualityRegimeOk'
if old_consider not in s:
    raise SystemExit("canConsider anchor not found")
s = s.replace(old_consider, new_consider)

anchor = 'var int seenClosedTrades = 0\nvar line[] historyLines'
if anchor not in s:
    raise SystemExit("seenClosedTrades anchor not found")
s = s.replace(anchor, '''var int seenClosedTrades = 0
var int firstFilledTime = na
var int bbmaClosed = 0
var int bbmaWins = 0
var int demandClosed = 0
var int demandWins = 0
var int supplyClosed = 0
var int supplyWins = 0
var int liqClosed = 0
var int liqWins = 0
var int breakClosed = 0
var int breakWins = 0
var line[] historyLines''')

old_open = '''    if orderPending
        dayTrades += 1
        weekTrades += 1
    orderPending := false'''
new_open = '''    if orderPending
        dayTrades += 1
        weekTrades += 1
    if na(firstFilledTime)
        firstFilledTime := time
    orderPending := false'''
if old_open not in s:
    raise SystemExit("open anchor not found")
s = s.replace(old_open, new_open)

old_close = '''newClosedTrade = strategy.closedtrades > seenClosedTrades
if newClosedTrade
    seenClosedTrades := strategy.closedtrades
    activeDirection := 0
'''
new_close = '''newClosedTrade = strategy.closedtrades > seenClosedTrades
if newClosedTrade
    lastClosedIndex = strategy.closedtrades - 1
    lastClosedProfit = strategy.closedtrades.profit(lastClosedIndex)
    lastWasWin = lastClosedProfit > 0
    if activePlaybook == "BBMA_REENTRY"
        bbmaClosed += 1
        bbmaWins += lastWasWin ? 1 : 0
    else if activePlaybook == "DEMAND_REJECT"
        demandClosed += 1
        demandWins += lastWasWin ? 1 : 0
    else if activePlaybook == "SUPPLY_REJECT"
        supplyClosed += 1
        supplyWins += lastWasWin ? 1 : 0
    else if activePlaybook == "LIQ_FVG"
        liqClosed += 1
        liqWins += lastWasWin ? 1 : 0
    else if activePlaybook == "BREAK_RETEST"
        breakClosed += 1
        breakWins += lastWasWin ? 1 : 0
    seenClosedTrades := strategy.closedtrades
    activeDirection := 0
'''
if old_close not in s:
    raise SystemExit("close anchor not found")
s = s.replace(old_close, new_close)

old_metrics = '''closedTrades = strategy.closedtrades
winRate = closedTrades > 0 ? strategy.wintrades * 100.0 / closedTrades : na
profitFactor = math.abs(strategy.grossloss) > 0 ? strategy.grossprofit / math.abs(strategy.grossloss) : na
strategyDirection = strategy.position_size > 0 ? 1 : strategy.position_size < 0 ? -1 : 0
'''
new_metrics = '''closedTrades = strategy.closedtrades
winRate = closedTrades > 0 ? strategy.wintrades * 100.0 / closedTrades : na
profitFactor = math.abs(strategy.grossloss) > 0 ? strategy.grossprofit / math.abs(strategy.grossloss) : na
elapsedWeeks = not na(firstFilledTime) ? math.max((time - firstFilledTime) / 604800000.0, 1.0 / 7.0) : na
actualTradesPerWeek = not na(elapsedWeeks) and elapsedWeeks > 0 ? closedTrades / elapsedWeeks : na
strategyDirection = strategy.position_size > 0 ? 1 : strategy.position_size < 0 ? -1 : 0
'''
if old_metrics not in s:
    raise SystemExit("metrics anchor not found")
s = s.replace(old_metrics, new_metrics)

func_anchor = 'f_bias(v) => v == 1 ? "BULL" : v == -1 ? "BEAR" : "NEUTRAL"\n\nvar table dash = table.new(position.top_right, 2, 16,'
if func_anchor not in s:
    raise SystemExit("table function anchor not found")
s = s.replace(func_anchor, 'f_bias(v) => v == 1 ? "BULL" : v == -1 ? "BEAR" : "NEUTRAL"\nf_wr(w, n) => n > 0 ? str.tostring(w * 100.0 / n, "#.0") + "% (" + str.tostring(w) + "/" + str.tostring(n) + ")" : "—"\n\nvar table dash = table.new(position.top_right, 2, 21,')

old_tail = '''    table.cell(dash, 0, 15, "MAX DRAWDOWN", text_color=color.silver)
    table.cell(dash, 1, 15, str.tostring(strategy.max_drawdown, "#.##"), text_color=color.white)
else if barstate.islast
    table.clear(dash, 0, 0, 1, 15)'''
new_tail = '''    table.cell(dash, 0, 15, "MAX DRAWDOWN", text_color=color.silver)
    table.cell(dash, 1, 15, str.tostring(strategy.max_drawdown, "#.##"), text_color=color.white)
    table.cell(dash, 0, 16, "ACTUAL TRADES/WK", text_color=color.silver)
    table.cell(dash, 1, 16, f_num(actualTradesPerWeek), text_color=not na(actualTradesPerWeek) and actualTradesPerWeek >= weeklyTarget ? color.lime : color.white)
    table.cell(dash, 0, 17, "BBMA W/R", text_color=color.silver)
    table.cell(dash, 1, 17, f_wr(bbmaWins, bbmaClosed), text_color=color.white)
    table.cell(dash, 0, 18, "DEMAND W/R", text_color=color.silver)
    table.cell(dash, 1, 18, f_wr(demandWins, demandClosed), text_color=color.white)
    table.cell(dash, 0, 19, "SUPPLY W/R", text_color=color.silver)
    table.cell(dash, 1, 19, f_wr(supplyWins, supplyClosed), text_color=color.white)
    table.cell(dash, 0, 20, "LIQ / BREAK W/R", text_color=color.silver)
    table.cell(dash, 1, 20, f_wr(liqWins + breakWins, liqClosed + breakClosed), text_color=color.white)
else if barstate.islast
    table.clear(dash, 0, 0, 1, 20)'''
if old_tail not in s:
    raise SystemExit("dashboard tail not found")
s = s.replace(old_tail, new_tail)

if "lookahead=barmerge.lookahead_on" in s:
    raise SystemExit("lookahead_on remains")

p.write_text(s)
