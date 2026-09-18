using System;
using System.Text;
using cAlgo.API;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    // Email-only transport around the same frozen RR10 selection gate used by TradingView.
    public class CasioRegimeRouterSignal : Robot
    {
        [Parameter("Enable Email", Group = "Email", DefaultValue = true)]
        public bool EmailEnabled { get; set; }

        [Parameter("Recipient Email", Group = "Email", DefaultValue = "farhanshoffi@moe.gov.my")]
        public string RecipientEmail { get; set; }

        [Parameter("Sender Email", Group = "Email", DefaultValue = "farhanshoffi@moe.gov.my")]
        public string SenderEmail { get; set; }

        [Parameter("Send Test Email On Start", Group = "Email", DefaultValue = true)]
        public bool SendTestEmailOnStart { get; set; }

        [Parameter("Email Exit Notice", Group = "Email", DefaultValue = false)]
        public bool EmailExitNotice { get; set; }

        // RR10 canonical constants. Keep these frozen across Python, Pine and cTrader.
        private const double RiskPercent = 5.0;
        private const double TrendAdxThreshold = 18.0;
        private const int SupportBars = 2;
        private const double CanonicalTargetR = 3.0;

        [Parameter("Signal Only", Group = "Safety", DefaultValue = true)]
        public bool SignalOnly { get; set; }

        private Bars _h1Bars;
        private Bars _h4Bars;
        private Bars _d1Bars;

        private ExponentialMovingAverage _m15Ema20;
        private ExponentialMovingAverage _m15Ema50;
        private ExponentialMovingAverage _h1Ema20;
        private ExponentialMovingAverage _h1Ema50;
        private ExponentialMovingAverage _h4Ema20;
        private ExponentialMovingAverage _h4Ema50;
        private AverageTrueRange _m15Atr;
        private DirectionalMovementSystem _m15Dms;
        private DirectionalMovementSystem _h4Dms;

        private long _seq;
        private long _last0591Long = -1000000;
        private long _last0591Short = -1000000;
        private long _lastV1Long = -1000000;
        private long _lastV1Short = -1000000;
        private long _lastOutLong = -1000000;
        private long _lastOutShort = -1000000;
        private long _lastSpLong = -1000000;
        private long _lastSpShort = -1000000;
        private long _lastSfLong = -1000000;
        private long _lastSfShort = -1000000;

        private int _m0591State;
        private long _m0591ImpulseSeq;
        private double _m0591ImpOpen;
        private double _m0591ImpClose;
        private double _m0591ImpHigh;
        private double _m0591ImpLow;
        private double _m0591ImpAtr;
        private double _m0591Broken;
        private double _m0591PullExtreme;

        private bool _virtualActive;
        private int _virtualDir;
        private double _virtualEntry;
        private double _virtualStop;
        private double _virtualTarget;
        private double _virtualR;
        private string _virtualTechnique = string.Empty;
        private DateTime _virtualOpened;

        protected override void OnStart()
        {
            if (!SymbolName.ToUpperInvariant().Contains("XAUUSD"))
            {
                Print("CASIO Regime Router must run on XAUUSD. Current symbol: {0}", SymbolName);
                Stop();
                return;
            }

            if (TimeFrame != TimeFrame.Minute15)
            {
                Print("CASIO Regime Router must run on M15. Current timeframe: {0}", TimeFrame);
                Stop();
                return;
            }

            _h1Bars = MarketData.GetBars(TimeFrame.Hour, SymbolName);
            _h4Bars = MarketData.GetBars(TimeFrame.Hour4, SymbolName);
            _d1Bars = MarketData.GetBars(TimeFrame.Daily, SymbolName);

            EnsureHistory(Bars, 300);
            EnsureHistory(_h1Bars, 120);
            EnsureHistory(_h4Bars, 120);
            EnsureHistory(_d1Bars, 20);

            _m15Ema20 = Indicators.ExponentialMovingAverage(Bars.ClosePrices, 20);
            _m15Ema50 = Indicators.ExponentialMovingAverage(Bars.ClosePrices, 50);
            _h1Ema20 = Indicators.ExponentialMovingAverage(_h1Bars.ClosePrices, 20);
            _h1Ema50 = Indicators.ExponentialMovingAverage(_h1Bars.ClosePrices, 50);
            _h4Ema20 = Indicators.ExponentialMovingAverage(_h4Bars.ClosePrices, 20);
            _h4Ema50 = Indicators.ExponentialMovingAverage(_h4Bars.ClosePrices, 50);
            _m15Atr = Indicators.AverageTrueRange(Bars, 14, MovingAverageType.WilderSmoothing);
            _m15Dms = Indicators.DirectionalMovementSystem(Bars, 14, MovingAverageType.WilderSmoothing);
            _h4Dms = Indicators.DirectionalMovementSystem(_h4Bars, 14, MovingAverageType.WilderSmoothing);

            Print("CASIO RR10 canonical EMAIL engine started on {0} M15.", SymbolName);
            Print("Frozen parity: 0591 live selection only | 3R | support=2 | H4 ADX=18 | entry=M15 close.");
            Print("Email enabled: {0} | Sender: {1} | Recipient: {2}", EmailEnabled, SenderEmail, RecipientEmail);
            Print("Signal-only mode: {0}. No orders will be placed.", SignalOnly);

            if (SendTestEmailOnStart)
                SendTestEmail();
        }

        protected override void OnBarClosed()
        {
            if (Bars.Count < 80 || _h1Bars.Count < 60 || _h4Bars.Count < 60 || _d1Bars.Count < 3)
                return;

            _seq++;
            UpdateVirtualTrade();

            if (_virtualActive)
                return;

            var bar = Bars.LastBar;
            var atr = _m15Atr.Result.Last(0);
            if (double.IsNaN(atr) || atr <= 0)
                return;

            var ema20 = _m15Ema20.Result.Last(0);
            var ema50 = _m15Ema50.Result.Last(0);
            var adx = _m15Dms.ADX.Last(0);

            var range = Math.Max(bar.High - bar.Low, Symbol.TickSize);
            var bodyFrac = Math.Abs(bar.Close - bar.Open) / range;
            var closeLoc = (bar.Close - bar.Low) / range;
            var rangeAtr = range / atr;
            var bull = bar.Close > bar.Open;
            var bear = bar.Close < bar.Open;

            var hh5 = HighestHigh(1, 5);
            var ll5 = LowestLow(1, 5);
            var hh10 = HighestHigh(1, 10);
            var ll10 = LowestLow(1, 10);
            var hh20 = HighestHigh(1, 20);
            var ll20 = LowestLow(1, 20);

            var bullFvg = bar.Low > Bars.HighPrices.Last(2);
            var bearFvg = bar.High < Bars.LowPrices.Last(2);

            var dispLong = bull && bodyFrac >= 0.55 && closeLoc >= 0.68 && rangeAtr >= 0.80 && bar.Close > hh5;
            var dispShort = bear && bodyFrac >= 0.55 && closeLoc <= 0.32 && rangeAtr >= 0.80 && bar.Close < ll5;

            var sellSweepAge = BarsSinceSellSweep(6);
            var buySweepAge = BarsSinceBuySweep(6);
            var primary = IsPrimarySession(bar.OpenTime);

            var h1Index = 1;
            var h4Index = 1;
            var h1Close = _h1Bars.ClosePrices.Last(h1Index);
            var h1E20 = _h1Ema20.Result.Last(h1Index);
            var h1E50 = _h1Ema50.Result.Last(h1Index);
            var h4Close = _h4Bars.ClosePrices.Last(h4Index);
            var h4E20 = _h4Ema20.Result.Last(h4Index);
            var h4E50 = _h4Ema50.Result.Last(h4Index);
            var h4Adx = _h4Dms.ADX.Last(h4Index);

            var h1Bias = Bias(h1Close, h1E20, h1E50);
            var h4Bias = Bias(h4Close, h4E20, h4E50);
            var htfLong = h1Bias >= 0 && h4Bias >= 0;
            var htfShort = h1Bias <= 0 && h4Bias <= 0;
            var strongLong = h1Bias == 1 && h4Bias == 1;
            var strongShort = h1Bias == -1 && h4Bias == -1;
            var strongTrend = h1Bias != 0 && h1Bias == h4Bias && h4Adx >= TrendAdxThreshold;

            var prevDayHigh = _d1Bars.HighPrices.Last(1);
            var prevDayLow = _d1Bars.LowPrices.Last(1);

            var v1Long = ema20 > ema50 && bar.Close > hh10 && bull && bodyFrac >= 0.45;
            var v1Short = ema20 < ema50 && bar.Close < ll10 && bear && bodyFrac >= 0.45;
            var v1Dir = BoolDir(v1Long, v1Short);
            var v1Q = (adx > 22 ? 1 : 0) + (strongLong ? 1 : 0) + (strongShort ? 1 : 0);
            var v1R = QualityTarget(v1Q);

            var outLong = primary && ((sellSweepAge <= 2 && bullFvg) || (strongLong && dispLong && bar.Low <= ema20 + 0.25 * atr));
            var outShort = primary && ((buySweepAge <= 2 && bearFvg) || (strongShort && dispShort && bar.High >= ema20 - 0.25 * atr));
            var outDir = BoolDir(outLong, outShort);
            var outQ = ((bullFvg || bearFvg) ? 1 : 0) + ((dispLong || dispShort) ? 1 : 0) + ((strongLong || strongShort) ? 1 : 0);
            var outR = QualityTarget(outQ);

            var sfLong = primary && htfLong && sellSweepAge <= 6 && (dispLong || bullFvg);
            var sfShort = primary && htfShort && buySweepAge <= 6 && (dispShort || bearFvg);
            var sfDir = BoolDir(sfLong, sfShort);
            var sfQ = ((strongLong || strongShort) ? 1 : 0) + ((bullFvg || bearFvg) ? 1 : 0) + (rangeAtr > 1 ? 1 : 0);
            var sfR = QualityTarget(sfQ);

            var spPbLong = strongLong && sellSweepAge <= 5 && bullFvg;
            var spPbShort = strongShort && buySweepAge <= 5 && bearFvg;
            var spSwLong = htfLong && sellSweepAge <= 2 && bullFvg;
            var spSwShort = htfShort && buySweepAge <= 2 && bearFvg;
            var spRtLong = primary && htfLong && bar.Low <= prevDayHigh + 0.15 * atr && bar.Close > prevDayHigh && bullFvg;
            var spRtShort = primary && htfShort && bar.High >= prevDayLow - 0.15 * atr && bar.Close < prevDayLow && bearFvg;
            var spBaseLong = spPbLong || spSwLong || spRtLong;
            var spBaseShort = spPbShort || spSwShort || spRtShort;
            var spQ = (primary ? 1 : 0) + ((strongLong || strongShort) ? 1 : 0) + ((bullFvg || bearFvg) ? 1 : 0) + ((dispLong || dispShort) ? 1 : 0);
            var spBaseR = QualityTarget(spQ);
            double spLongR;
            double spShortR;
            var spLongAllowed = MtfAllowed(spBaseR, 1, h1Bias, h4Bias, h4Adx, out spLongR);
            var spShortAllowed = MtfAllowed(spBaseR, -1, h1Bias, h4Bias, h4Adx, out spShortR);
            var spLong = spBaseLong && spLongAllowed;
            var spShort = spBaseShort && spShortAllowed;
            var spDir = BoolDir(spLong, spShort);
            var spR = spDir == 1 ? spLongR : spDir == -1 ? spShortR : spBaseR;

            double m0591Stop;
            double m0591R;
            var m0591Dir = Update0591(bar, atr, rangeAtr, bodyFrac, closeLoc, hh20, ll20, h1Bias, h4Bias, h4Adx, out m0591Stop, out m0591R);

            MarkSignals(m0591Dir, v1Dir, outDir, spDir, sfDir);

            // RR10 is the only live selection. The other techniques above are confirmations only.
            var supportDir = m0591Dir == 0 ? 0 : SupportCount(m0591Dir);
            var alignCount = m0591Dir == 0 ? 0 : (h1Bias == m0591Dir ? 1 : 0) + (h4Bias == m0591Dir ? 1 : 0);
            var oldRouterSelected0591 = strongTrend
                ? m0591Dir != 0 && m0591Dir == h1Bias
                : spDir == 0 && m0591Dir != 0 && supportDir >= 2;
            var canonicalDir = oldRouterSelected0591 && !primary && alignCount >= 1 ? m0591Dir : 0;

            var finalDir = canonicalDir;
            var selected = canonicalDir == 0 ? "WAIT" : "RR10 Canonical / 0591";
            var selectedR = canonicalDir == 0 ? double.NaN : CanonicalTargetR;
            var selectedStop = canonicalDir == 0 ? double.NaN : m0591Stop;

            if (finalDir == 0 || double.IsNaN(selectedStop) || double.IsNaN(selectedR))
                return;

            var entry = bar.Close;
            var riskDistance = Math.Abs(entry - selectedStop);
            if (riskDistance <= 0)
                return;

            var target = entry + finalDir * selectedR * riskDistance;
            var stopPips = riskDistance / Symbol.PipSize;
            var volumeUnits = Symbol.VolumeForProportionalRisk(ProportionalAmountType.Equity, RiskPercent, stopPips, RoundingMode.Down);
            var lots = Symbol.VolumeInUnitsToQuantity(volumeUnits);

            _virtualActive = true;
            _virtualDir = finalDir;
            _virtualEntry = entry;
            _virtualStop = selectedStop;
            _virtualTarget = target;
            _virtualR = selectedR;
            _virtualTechnique = selected;
            _virtualOpened = Server.Time;

            var routerMode = strongTrend ? "TREND" : "MIXED";
            SendSignalEmail(finalDir, routerMode, selected, selectedR, entry, selectedStop, target, h1Bias, h4Bias, h4Adx, lots, volumeUnits, SupportCount(1), SupportCount(-1));
        }

        private void SendSignalEmail(int dir, string routerMode, string technique, double rr, double entry, double stop, double target, int h1Bias, int h4Bias, double h4Adx, double lots, double volumeUnits, int longSupport, int shortSupport)
        {
            if (!EmailEnabled)
            {
                Print("CASIO RR10 email skipped: Enable Email is false.");
                return;
            }

            var side = dir == 1 ? "LONG" : "SHORT";
            var subject = string.Format("[CASIO RR10] XAUUSD {0} | {1}", side, routerMode);
            var body = new StringBuilder();
            body.AppendLine("CASIO RR10 canonical Regime Router signal");
            body.AppendLine("Same live selection gate as TradingView RR10.");
            body.AppendLine();
            body.AppendLine("Symbol: " + SymbolName);
            body.AppendLine("Time: " + Server.Time.ToString("yyyy-MM-dd HH:mm:ss") + " UTC");
            body.AppendLine("Direction: " + side);
            body.AppendLine("Router: " + routerMode);
            body.AppendLine("Engine: RR10");
            body.AppendLine("Live technique: RR10 Canonical / 0591");
            body.AppendLine("Entry: " + Fmt(entry));
            body.AppendLine("Stop loss: " + Fmt(stop));
            body.AppendLine("Take profit: " + Fmt(target));
            body.AppendLine("Target: 3R");
            body.AppendLine("Risk model: 5% of current equity");
            body.AppendLine("Approx. volume: " + lots.ToString("0.####") + " lots (" + volumeUnits.ToString("0") + " units)");
            body.AppendLine("H1 bias: " + BiasText(h1Bias));
            body.AppendLine("H4 bias: " + BiasText(h4Bias));
            body.AppendLine("H4 ADX: " + h4Adx.ToString("0.00"));
            body.AppendLine("Agreement window: " + longSupport + " long / " + shortSupport + " short");
            body.AppendLine();
            body.AppendLine("Signal-only cBot: no order was placed automatically.");

            TrySendEmail(subject, body.ToString(), "signal");
        }

        private void SendTestEmail()
        {
            if (!EmailEnabled)
            {
                Print("CASIO RR10 startup email test skipped: Enable Email is false.");
                return;
            }

            var body = new StringBuilder();
            body.AppendLine("CASIO RR10 email transport test");
            body.AppendLine();
            body.AppendLine("This is only an email test; it is not a trading signal.");
            body.AppendLine("Engine: RR10");
            body.AppendLine("Symbol: " + SymbolName);
            body.AppendLine("Time: " + Server.Time.ToString("yyyy-MM-dd HH:mm:ss") + " UTC");
            body.AppendLine("Frozen parity: 0591 live selection only | 3R | support=2 | H4 ADX=18.");
            body.AppendLine("Sender: " + SenderEmail);
            body.AppendLine("Recipient: " + RecipientEmail);

            TrySendEmail("[CASIO RR10] cTrader email TEST", body.ToString(), "startup-test");
        }

        private bool TrySendEmail(string subject, string body, string context)
        {
            if (string.IsNullOrWhiteSpace(SenderEmail) || string.IsNullOrWhiteSpace(RecipientEmail))
            {
                Print("CASIO RR10 EMAIL FAILED ({0}): Sender Email or Recipient Email is blank.", context);
                return false;
            }

            try
            {
                Notifications.SendEmail(SenderEmail.Trim(), RecipientEmail.Trim(), subject, body);
                Print("CASIO RR10 email request accepted ({0}): {1}", context, subject);
                return true;
            }
            catch (Exception ex)
            {
                Print("CASIO RR10 EMAIL FAILED ({0}): {1}: {2}", context, ex.GetType().Name, ex.Message);
                Print("Check cTrader Settings/Preferences -> Advanced -> Email: Enable email, SMTP host/port, SSL, username and password.");
                return false;
            }
        }

        private void UpdateVirtualTrade()
        {
            if (!_virtualActive)
                return;

            var bar = Bars.LastBar;
            var stopHit = _virtualDir == 1 ? bar.Low <= _virtualStop : bar.High >= _virtualStop;
            var targetHit = _virtualDir == 1 ? bar.High >= _virtualTarget : bar.Low <= _virtualTarget;

            if (!stopHit && !targetHit)
                return;

            var result = stopHit ? "STOP" : "TARGET"; // same-bar collision is stop-first
            if (EmailEnabled && EmailExitNotice)
            {
                var subject = string.Format("[CASIO RR10] {0} {1}", SymbolName, result);
                var body = string.Format("RR10 virtual signal closed by {0}.\nOpened: {1:yyyy-MM-dd HH:mm:ss} UTC\nEntry: {2}\nSL: {3}\nTP: {4}\nTarget: {5:0}R",
                    result, _virtualOpened, Fmt(_virtualEntry), Fmt(_virtualStop), Fmt(_virtualTarget), _virtualR);
                TrySendEmail(subject, body, "exit-" + result.ToLowerInvariant());
            }

            _virtualActive = false;
            _virtualTechnique = string.Empty;
        }

        private int Update0591(Bar bar, double atr, double rangeAtr, double bodyFrac, double closeLoc, double hh20, double ll20, int h1Bias, int h4Bias, double h4Adx, out double stop, out double rr)
        {
            stop = double.NaN;
            rr = double.NaN;
            var impLong = rangeAtr >= 1.20 && bodyFrac >= 0.55 && closeLoc >= 0.72 && bar.Close > hh20;
            var impShort = rangeAtr >= 1.20 && bodyFrac >= 0.55 && closeLoc <= 0.28 && bar.Close < ll20;

            if (_m0591State == 0)
            {
                if (impLong && !impShort)
                {
                    _m0591State = 1;
                    _m0591ImpulseSeq = _seq;
                    _m0591ImpOpen = bar.Open;
                    _m0591ImpClose = bar.Close;
                    _m0591ImpHigh = bar.High;
                    _m0591ImpLow = bar.Low;
                    _m0591ImpAtr = atr;
                    _m0591Broken = hh20;
                    _m0591PullExtreme = bar.Low;
                }
                else if (impShort && !impLong)
                {
                    _m0591State = -1;
                    _m0591ImpulseSeq = _seq;
                    _m0591ImpOpen = bar.Open;
                    _m0591ImpClose = bar.Close;
                    _m0591ImpHigh = bar.High;
                    _m0591ImpLow = bar.Low;
                    _m0591ImpAtr = atr;
                    _m0591Broken = ll20;
                    _m0591PullExtreme = bar.High;
                }
                return 0;
            }

            if (_seq <= _m0591ImpulseSeq)
                return 0;

            var age = _seq - _m0591ImpulseSeq;
            var impBody = Math.Abs(_m0591ImpClose - _m0591ImpOpen);
            if (age > 4)
            {
                _m0591State = 0;
                return 0;
            }

            if (_m0591State == 1)
            {
                _m0591PullExtreme = Math.Min(_m0591PullExtreme, bar.Low);
                var invalid = bar.Low < _m0591ImpLow - 0.30 * _m0591ImpAtr;
                var zoneNear = _m0591ImpClose - 0.18 * impBody;
                var zoneFar = _m0591ImpClose - 0.50 * impBody;
                var touched = bar.Low <= zoneNear && bar.High >= zoneFar;
                var confirm = bar.Close > bar.Open && bar.Close > _m0591Broken;
                if (invalid)
                {
                    _m0591State = 0;
                    return 0;
                }
                if (touched && confirm)
                {
                    double targetR;
                    var allowed = MtfAllowed(3.0, 1, h1Bias, h4Bias, h4Adx, out targetR);
                    _m0591State = 0;
                    if (allowed)
                    {
                        stop = _m0591PullExtreme - 0.12 * _m0591ImpAtr;
                        rr = targetR;
                        return 1;
                    }
                }
            }
            else
            {
                _m0591PullExtreme = Math.Max(_m0591PullExtreme, bar.High);
                var invalid = bar.High > _m0591ImpHigh + 0.30 * _m0591ImpAtr;
                var zoneNear = _m0591ImpClose + 0.18 * impBody;
                var zoneFar = _m0591ImpClose + 0.50 * impBody;
                var touched = bar.High >= zoneNear && bar.Low <= zoneFar;
                var confirm = bar.Close < bar.Open && bar.Close < _m0591Broken;
                if (invalid)
                {
                    _m0591State = 0;
                    return 0;
                }
                if (touched && confirm)
                {
                    double targetR;
                    var allowed = MtfAllowed(3.0, -1, h1Bias, h4Bias, h4Adx, out targetR);
                    _m0591State = 0;
                    if (allowed)
                    {
                        stop = _m0591PullExtreme + 0.12 * _m0591ImpAtr;
                        rr = targetR;
                        return -1;
                    }
                }
            }

            return 0;
        }

        private bool MtfAllowed(double baseR, int dir, int h1, int h4, double h4Adx, out double target)
        {
            var blocked = h1 == -dir && h4 == -dir;
            var baseGrade = baseR >= 4.0 ? 2 : baseR >= 3.0 ? 1 : 0;
            var align = (h1 == dir ? 1 : 0) + (h4 == dir ? 1 : 0);
            var strong = align == 2 && h4Adx >= TrendAdxThreshold ? 1 : 0;
            var score = baseGrade + align + strong;
            target = score >= 3 ? 4.0 : score >= 1 ? 3.0 : 2.0;
            return !blocked;
        }

        private void MarkSignals(int m0591, int v1, int outcome, int sp, int sf)
        {
            Mark(m0591, ref _last0591Long, ref _last0591Short);
            Mark(v1, ref _lastV1Long, ref _lastV1Short);
            Mark(outcome, ref _lastOutLong, ref _lastOutShort);
            Mark(sp, ref _lastSpLong, ref _lastSpShort);
            Mark(sf, ref _lastSfLong, ref _lastSfShort);
        }

        private void Mark(int dir, ref long lastLong, ref long lastShort)
        {
            if (dir == 1) lastLong = _seq;
            if (dir == -1) lastShort = _seq;
        }

        private int SupportCount(int dir)
        {
            var count = 0;
            count += Recent(dir == 1 ? _last0591Long : _last0591Short) ? 1 : 0;
            count += Recent(dir == 1 ? _lastV1Long : _lastV1Short) ? 1 : 0;
            count += Recent(dir == 1 ? _lastOutLong : _lastOutShort) ? 1 : 0;
            count += Recent(dir == 1 ? _lastSpLong : _lastSpShort) ? 1 : 0;
            count += Recent(dir == 1 ? _lastSfLong : _lastSfShort) ? 1 : 0;
            return count;
        }

        private bool Recent(long seq) => seq > -100000 && _seq - seq <= SupportBars;

        private int BarsSinceSellSweep(int maxAge)
        {
            for (var age = 0; age <= maxAge; age++)
                if (IsSellSweep(age)) return age;
            return 999;
        }

        private int BarsSinceBuySweep(int maxAge)
        {
            for (var age = 0; age <= maxAge; age++)
                if (IsBuySweep(age)) return age;
            return 999;
        }

        private bool IsSellSweep(int offset)
        {
            var low = Bars.LowPrices.Last(offset);
            var close = Bars.ClosePrices.Last(offset);
            var ll20 = LowestLow(offset + 1, 20);
            return low < ll20 && close > ll20;
        }

        private bool IsBuySweep(int offset)
        {
            var high = Bars.HighPrices.Last(offset);
            var close = Bars.ClosePrices.Last(offset);
            var hh20 = HighestHigh(offset + 1, 20);
            return high > hh20 && close < hh20;
        }

        private double HighestHigh(int startOffset, int count)
        {
            var value = double.MinValue;
            for (var i = startOffset; i < startOffset + count; i++)
                value = Math.Max(value, Bars.HighPrices.Last(i));
            return value;
        }

        private double LowestLow(int startOffset, int count)
        {
            var value = double.MaxValue;
            for (var i = startOffset; i < startOffset + count; i++)
                value = Math.Min(value, Bars.LowPrices.Last(i));
            return value;
        }

        private static int Bias(double close, double ema20, double ema50)
        {
            if (ema20 > ema50 && close > ema20) return 1;
            if (ema20 < ema50 && close < ema20) return -1;
            return 0;
        }

        private static string BiasText(int bias) => bias == 1 ? "BULL" : bias == -1 ? "BEAR" : "NEUTRAL";

        private static int BoolDir(bool longSignal, bool shortSignal)
        {
            if (longSignal && !shortSignal) return 1;
            if (shortSignal && !longSignal) return -1;
            return 0;
        }

        private static double QualityTarget(int q) => q >= 4 ? 4.0 : q >= 2 ? 3.0 : 2.0;

        private static bool IsPrimarySession(DateTime time)
        {
            var minutes = time.Hour * 60 + time.Minute;
            return (minutes >= 420 && minutes < 720) || (minutes >= 750 && minutes < 1020);
        }

        private void Select(int dir, string name, double rr, double stop, ref int finalDir, ref string selected, ref double selectedR, ref double selectedStop)
        {
            finalDir = dir;
            selected = name;
            selectedR = rr;
            selectedStop = stop;
        }

        private void EnsureHistory(Bars bars, int minimum)
        {
            var guard = 0;
            while (bars.Count < minimum && guard < 10)
            {
                var loaded = bars.LoadMoreHistory();
                if (loaded <= 0) break;
                guard++;
            }
        }

        private string Fmt(double value) => value.ToString("F" + Math.Max(2, Symbol.Digits));
    }
}
