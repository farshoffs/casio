using System;
using System.Globalization;
using System.IO;
using System.Text;
using cAlgo.API;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class CasioFxProM15CsvExporter : Robot
    {
        private const string Header = "time_utc,open,high,low,close,tick_volume,symbol,timeframe";

        [Parameter("Start Date UTC", Group = "History", DefaultValue = "2024-01-01")]
        public string StartDateUtc { get; set; }

        [Parameter("Max History Loads", Group = "History", DefaultValue = 500, MinValue = 1, MaxValue = 5000)]
        public int MaxHistoryLoads { get; set; }

        [Parameter("Rebuild CSV On Start", Group = "History", DefaultValue = false)]
        public bool RebuildCsvOnStart { get; set; }

        [Parameter("CSV File Name", Group = "File", DefaultValue = "fxpro_xauusd_m15.csv")]
        public string CsvFileName { get; set; }

        [Parameter("Append New M15 Bars", Group = "Live", DefaultValue = true)]
        public bool AppendNewBars { get; set; }

        [Parameter("Require XAUUSD", Group = "Safety", DefaultValue = true)]
        public bool RequireXauUsd { get; set; }

        private Bars _m15Bars;
        private DateTime _startUtc;
        private DateTime? _lastWrittenOpenTime;
        private string _fileName;
        private readonly CultureInfo _invariant = CultureInfo.InvariantCulture;

        protected override void OnStart()
        {
            if (RequireXauUsd && !SymbolName.ToUpperInvariant().Contains("XAUUSD"))
            {
                Print("CASIO CSV exporter stopped: attach it to an XAUUSD symbol. Current symbol: {0}", SymbolName);
                Stop();
                return;
            }

            if (!TryParseUtcDate(StartDateUtc, out _startUtc))
            {
                Print("CASIO CSV exporter stopped: Start Date UTC must be yyyy-MM-dd. Received: {0}", StartDateUtc);
                Stop();
                return;
            }

            _fileName = NormalizeFileName(CsvFileName);
            if (string.IsNullOrWhiteSpace(_fileName))
            {
                Print("CASIO CSV exporter stopped: CSV File Name is invalid.");
                Stop();
                return;
            }

            _m15Bars = MarketData.GetBars(TimeFrame.Minute15, SymbolName);

            if (RebuildCsvOnStart && File.Exists(_fileName))
            {
                File.Delete(_fileName);
                Print("CASIO CSV exporter: existing file deleted for full rebuild.");
            }

            EnsureCsvHeader();
            _lastWrittenOpenTime = ReadLastWrittenOpenTime();

            var historyTarget = _lastWrittenOpenTime.HasValue && !RebuildCsvOnStart
                ? _lastWrittenOpenTime.Value
                : _startUtc;

            LoadHistoryTo(historyTarget);
            SyncClosedBarsToCsv();

            if (AppendNewBars)
            {
                _m15Bars.BarClosed += OnM15BarClosed;
                Print("CASIO CSV exporter: live M15 append enabled.");
            }
            else
            {
                Print("CASIO CSV exporter: historical export complete; live append disabled.");
            }

            Print("CASIO CSV exporter ready.");
            Print("Symbol: {0} | Timeframe: M15 | Start UTC: {1:yyyy-MM-dd}", SymbolName, _startUtc);
            Print("CSV: {0}", _fileName);
            Print("Last written M15 bar: {0}",
                _lastWrittenOpenTime.HasValue
                    ? _lastWrittenOpenTime.Value.ToString("yyyy-MM-dd HH:mm:ss 'UTC'", _invariant)
                    : "none");
            Print("Local file folder: Documents/cAlgo/Data/cBots/CasioFxProM15CsvExporter/");
        }

        protected override void OnStop()
        {
            if (_m15Bars != null)
                _m15Bars.BarClosed -= OnM15BarClosed;
        }

        private void OnM15BarClosed(BarClosedEventArgs args)
        {
            if (!AppendNewBars || args == null || args.Bars == null || args.Bars.Count == 0)
                return;

            // During BarClosed the just-opened bar is omitted, so LastBar is the bar
            // that has just completed.
            var closedBar = args.Bars.LastBar;
            AppendBarIfNew(closedBar);
        }

        private void LoadHistoryTo(DateTime targetUtc)
        {
            if (_m15Bars.Count == 0)
            {
                Print("CASIO CSV exporter: no M15 bars returned for {0}.", SymbolName);
                return;
            }

            DateTime serverFirst;
            try
            {
                serverFirst = _m15Bars.GetServerFirstBarOpenTime();
                Print("FxPro/cTrader first available M15 bar reported by server: {0:yyyy-MM-dd HH:mm:ss} UTC", serverFirst);
            }
            catch (Exception ex)
            {
                serverFirst = DateTime.MinValue;
                Print("CASIO CSV exporter: could not query server-first M15 time: {0}", ex.Message);
            }

            var loads = 0;
            while (_m15Bars.Count > 0 && _m15Bars.OpenTimes[0] > targetUtc && loads < MaxHistoryLoads)
            {
                var added = _m15Bars.LoadMoreHistory();
                loads++;

                if (added <= 0)
                    break;

                if (loads == 1 || loads % 10 == 0)
                {
                    Print("History load {0}: +{1} bars | earliest now {2:yyyy-MM-dd HH:mm:ss} UTC",
                        loads, added, _m15Bars.OpenTimes[0]);
                }

                if (serverFirst != DateTime.MinValue && _m15Bars.OpenTimes[0] <= serverFirst)
                    break;
            }

            if (_m15Bars.Count > 0 && _m15Bars.OpenTimes[0] > targetUtc)
            {
                Print("CASIO CSV exporter warning: requested target {0:yyyy-MM-dd} UTC was not reached.",
                    targetUtc);
                Print("Earliest loaded bar is {0:yyyy-MM-dd HH:mm:ss} UTC after {1} history load(s).",
                    _m15Bars.OpenTimes[0], loads);
            }
            else if (_m15Bars.Count > 0)
            {
                Print("History ready: earliest loaded M15 bar {0:yyyy-MM-dd HH:mm:ss} UTC ({1} bars in memory).",
                    _m15Bars.OpenTimes[0], _m15Bars.Count);
            }
        }

        private void SyncClosedBarsToCsv()
        {
            if (_m15Bars == null || _m15Bars.Count == 0)
                return;

            var buffer = new StringBuilder(512 * 1024);
            var appended = 0;

            for (var i = 0; i < _m15Bars.Count; i++)
            {
                var bar = _m15Bars[i];

                if (bar.OpenTime < _startUtc)
                    continue;

                if (!IsClosed(bar))
                    continue;

                if (_lastWrittenOpenTime.HasValue && bar.OpenTime <= _lastWrittenOpenTime.Value)
                    continue;

                buffer.AppendLine(ToCsvRow(bar));
                _lastWrittenOpenTime = bar.OpenTime;
                appended++;

                if (appended % 5000 == 0)
                {
                    File.AppendAllText(_fileName, buffer.ToString(), new UTF8Encoding(false));
                    buffer.Clear();
                }
            }

            if (buffer.Length > 0)
                File.AppendAllText(_fileName, buffer.ToString(), new UTF8Encoding(false));

            Print("CASIO CSV exporter sync: appended {0} closed M15 bar(s).", appended);
        }

        private void AppendBarIfNew(Bar bar)
        {
            if (bar.OpenTime < _startUtc)
                return;

            if (_lastWrittenOpenTime.HasValue && bar.OpenTime <= _lastWrittenOpenTime.Value)
                return;

            File.AppendAllText(_fileName, ToCsvRow(bar) + Environment.NewLine, new UTF8Encoding(false));
            _lastWrittenOpenTime = bar.OpenTime;

            Print("CSV appended: {0:yyyy-MM-dd HH:mm:ss} UTC | O {1} H {2} L {3} C {4} | ticks {5}",
                bar.OpenTime,
                FormatPrice(bar.Open),
                FormatPrice(bar.High),
                FormatPrice(bar.Low),
                FormatPrice(bar.Close),
                bar.TickVolume);
        }

        private bool IsClosed(Bar bar)
        {
            // M15 candle is complete 15 minutes after its open time.
            return bar.OpenTime.AddMinutes(15) <= Server.Time;
        }

        private void EnsureCsvHeader()
        {
            if (!File.Exists(_fileName))
            {
                File.WriteAllText(_fileName, Header + Environment.NewLine, new UTF8Encoding(false));
                return;
            }

            var info = new FileInfo(_fileName);
            if (info.Length == 0)
            {
                File.WriteAllText(_fileName, Header + Environment.NewLine, new UTF8Encoding(false));
                return;
            }

            string firstLine = null;
            foreach (var line in File.ReadLines(_fileName))
            {
                firstLine = line;
                break;
            }

            if (!string.Equals(firstLine, Header, StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    "Existing CSV header does not match CASIO exporter format. " +
                    "Use a different file name or enable Rebuild CSV On Start.");
            }
        }

        private DateTime? ReadLastWrittenOpenTime()
        {
            if (!File.Exists(_fileName))
                return null;

            string lastDataLine = null;
            foreach (var line in File.ReadLines(_fileName))
            {
                if (!string.IsNullOrWhiteSpace(line) && !line.StartsWith("time_utc,", StringComparison.Ordinal))
                    lastDataLine = line;
            }

            if (string.IsNullOrWhiteSpace(lastDataLine))
                return null;

            var comma = lastDataLine.IndexOf(',');
            if (comma <= 0)
                return null;

            var timestampText = lastDataLine.Substring(0, comma);
            DateTime parsed;
            if (DateTime.TryParseExact(
                timestampText,
                "yyyy-MM-dd'T'HH:mm:ss'Z'",
                _invariant,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out parsed))
            {
                return DateTime.SpecifyKind(parsed, DateTimeKind.Utc);
            }

            return null;
        }

        private string ToCsvRow(Bar bar)
        {
            return string.Join(",",
                bar.OpenTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", _invariant),
                FormatPrice(bar.Open),
                FormatPrice(bar.High),
                FormatPrice(bar.Low),
                FormatPrice(bar.Close),
                bar.TickVolume.ToString(_invariant),
                EscapeCsv(SymbolName),
                "M15");
        }

        private string FormatPrice(double value)
        {
            return value.ToString("F" + Math.Max(0, Symbol.Digits), _invariant);
        }

        private static string EscapeCsv(string value)
        {
            if (string.IsNullOrEmpty(value))
                return string.Empty;

            if (!value.Contains(",") && !value.Contains(""") && !value.Contains("\n") && !value.Contains("\r"))
                return value;

            return """ + value.Replace(""", """") + """;
        }

        private static string NormalizeFileName(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
                return null;

            var safe = Path.GetFileName(raw.Trim());
            if (string.IsNullOrWhiteSpace(safe))
                return null;

            if (!safe.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
                safe += ".csv";

            return safe;
        }

        private bool TryParseUtcDate(string text, out DateTime result)
        {
            DateTime parsed;
            var ok = DateTime.TryParseExact(
                text == null ? string.Empty : text.Trim(),
                "yyyy-MM-dd",
                _invariant,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out parsed);

            result = ok
                ? DateTime.SpecifyKind(parsed.Date, DateTimeKind.Utc)
                : DateTime.MinValue;

            return ok;
        }
    }
}
