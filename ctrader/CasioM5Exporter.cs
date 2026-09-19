using System;
using System.Globalization;
using System.IO;
using System.Text;
using cAlgo.API;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class CasioM5Exporter : Robot
    {
        [Parameter("Symbol Name", DefaultValue = "XAUUSD", Group = "Export")]
        public string ExportSymbol { get; set; }

        [Parameter("Start UTC", DefaultValue = "2017-01-01 00:00:00", Group = "Export")]
        public string StartUtc { get; set; }

        [Parameter("End UTC (blank = now)", DefaultValue = "", Group = "Export")]
        public string EndUtc { get; set; }

        [Parameter("Output File", DefaultValue = "fxpro_xauusd_m5.csv", Group = "Export")]
        public string OutputFile { get; set; }

        [Parameter("Completed Bars Only", DefaultValue = true, Group = "Export")]
        public bool CompletedBarsOnly { get; set; }

        [Parameter("Max History Loads", DefaultValue = 10000, MinValue = 1, Group = "Safety")]
        public int MaxHistoryLoads { get; set; }

        [Parameter("Progress Every N Loads", DefaultValue = 100, MinValue = 1, Group = "Safety")]
        public int ProgressEveryLoads { get; set; }

        protected override void OnStart()
        {
            try
            {
                var symbolName = (ExportSymbol ?? string.Empty).Trim();
                if (string.IsNullOrWhiteSpace(symbolName))
                    throw new ArgumentException("Symbol Name cannot be blank.");

                var start = ParseUtc(StartUtc, "Start UTC");
                var requestedEnd = string.IsNullOrWhiteSpace(EndUtc)
                    ? Server.Time
                    : ParseUtc(EndUtc, "End UTC");

                if (requestedEnd <= start)
                    throw new ArgumentException("End UTC must be later than Start UTC.");

                var fileName = Path.GetFileName((OutputFile ?? string.Empty).Trim());
                if (string.IsNullOrWhiteSpace(fileName))
                    fileName = "fxpro_xauusd_m5.csv";

                Print("CASIO M5 EXPORTER");
                Print("Symbol: {0}", symbolName);
                Print("Requested range: {0:yyyy-MM-dd HH:mm:ss} UTC -> {1:yyyy-MM-dd HH:mm:ss} UTC",
                    start, requestedEnd);

                var bars = MarketData.GetBars(TimeFrame.Minute5, symbolName);

                if (bars == null || bars.Count == 0)
                    throw new InvalidOperationException("cTrader returned no M5 bars for " + symbolName + ".");

                var serverFirst = bars.GetServerFirstBarOpenTime();
                Print("Server first available M5 bar: {0:yyyy-MM-dd HH:mm:ss} UTC", serverFirst);

                var loadCount = 0;
                var totalLoaded = 0;

                while (bars.Count > 0 && bars.OpenTimes[0] > start && loadCount < MaxHistoryLoads)
                {
                    var loaded = bars.LoadMoreHistory();
                    loadCount++;
                    totalLoaded += Math.Max(loaded, 0);

                    if (loadCount == 1 || loadCount % ProgressEveryLoads == 0)
                    {
                        Print(
                            "History load {0}: added {1}; total bars={2}; earliest={3:yyyy-MM-dd HH:mm:ss} UTC",
                            loadCount, loaded, bars.Count, bars.OpenTimes[0]
                        );
                    }

                    if (loaded <= 0)
                    {
                        Print("No more history returned by cTrader.");
                        break;
                    }
                }

                if (bars.OpenTimes[0] > start)
                {
                    Print(
                        "WARNING: requested start {0:yyyy-MM-dd HH:mm:ss} UTC was not reached. Earliest loaded bar is {1:yyyy-MM-dd HH:mm:ss} UTC.",
                        start, bars.OpenTimes[0]
                    );

                    if (loadCount >= MaxHistoryLoads)
                        Print("Max History Loads was reached. Increase it and rerun if more server history exists.");
                }

                var effectiveEnd = requestedEnd < Server.Time ? requestedEnd : Server.Time;
                var firstWritten = DateTime.MaxValue;
                var lastWritten = DateTime.MinValue;
                var rows = 0;

                using (var writer = new StreamWriter(fileName, false, new UTF8Encoding(false)))
                {
                    writer.WriteLine("time_utc,open,high,low,close,tick_volume,symbol,timeframe");

                    for (var i = 0; i < bars.Count; i++)
                    {
                        var bar = bars[i];
                        var openTime = bar.OpenTime;

                        if (openTime < start)
                            continue;

                        if (CompletedBarsOnly)
                        {
                            if (openTime.AddMinutes(5) > effectiveEnd)
                                continue;
                        }
                        else if (openTime > effectiveEnd)
                        {
                            continue;
                        }

                        writer.Write(openTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(bar.Open.ToString("G17", CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(bar.High.ToString("G17", CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(bar.Low.ToString("G17", CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(bar.Close.ToString("G17", CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(bar.TickVolume.ToString(CultureInfo.InvariantCulture));
                        writer.Write(',');
                        writer.Write(CsvEscape(symbolName));
                        writer.Write(',');
                        writer.WriteLine("M5");

                        rows++;
                        if (openTime < firstWritten) firstWritten = openTime;
                        if (openTime > lastWritten) lastWritten = openTime;
                    }
                }

                Print("--------------------------------------------------");
                Print("EXPORT COMPLETE");
                Print("File: {0}", fileName);
                Print("Rows: {0}", rows);
                Print("History loads: {0}", loadCount);
                Print("Additional bars loaded: {0}", totalLoaded);

                if (rows > 0)
                    Print("CSV range: {0:yyyy-MM-dd HH:mm:ss} UTC -> {1:yyyy-MM-dd HH:mm:ss} UTC", firstWritten, lastWritten);
                else
                    Print("WARNING: zero rows matched the requested range.");

                Print("cTrader stores the relative file under its permitted Documents/cAlgo/Data/cBots area.");
                Print("This exporter does not place or modify trades.");
            }
            catch (Exception ex)
            {
                Print("CASIO M5 EXPORT FAILED: {0}", ex.Message);
                Print(ex.ToString());
            }
            finally
            {
                Stop();
            }
        }

        private static DateTime ParseUtc(string text, string parameterName)
        {
            DateTime parsed;
            if (!DateTime.TryParse(
                    text,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AllowWhiteSpaces | DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                    out parsed))
            {
                throw new ArgumentException(parameterName + " must be a UTC date/time such as 2017-01-01 00:00:00.");
            }

            return DateTime.SpecifyKind(parsed, DateTimeKind.Utc);
        }

        private static string CsvEscape(string value)
        {
            if (value == null)
                return string.Empty;

            if (!value.Contains(",") && !value.Contains(""") && !value.Contains("\r") && !value.Contains("\n"))
                return value;

            return """ + value.Replace(""", """") + """;
        }
    }
}
