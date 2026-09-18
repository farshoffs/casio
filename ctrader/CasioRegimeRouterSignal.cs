using cAlgo.API;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class CasioRegimeRouterSignal : Robot
    {
        protected override void OnStart()
        {
            Print("CASIO RR10 cBot is retired as a live signal engine. TradingView FxPro RR10 is the single live state owner. Stop/remove this cBot and use the RR10 cross-device plugin.");
            Stop();
        }
    }
}
