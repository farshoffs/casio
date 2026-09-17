# CASIO Regime Router — FxPro cTrader Email Signals

This setup sends live CASIO Regime Router signals directly from an FxPro cTrader account to:

**farhanshoffi@moe.gov.my**

It does **not** depend on TradingView alerts, Vercel, Apps Script, or a paid TradingView plan.

## Architecture

- TradingView Pine = dashboard + visual backtest
- FxPro cTrader cBot = live M15/H1/H4 Regime Router signal engine
- cTrader `Notifications.SendEmail()` = signal delivery
- Recipient = `farhanshoffi@moe.gov.my`

The cBot is signal-only. It does not place orders.

## Requirement: FxPro cTrader account

The bot must run under an FxPro **cTrader** account/cTID. If the existing FxPro trading account is MT4 or MT5 only, create an additional cTrader account in FxPro Direct first. It can be demo for initial testing.

## File

`ctrader/CasioRegimeRouterSignal.cs`

## 1. Configure email in cTrader

On cTrader Desktop:

1. Open **Settings**.
2. Open **Advanced → Email**.
3. Enable email notifications.
4. Enable SSL if required by the sender mailbox.
5. Enter the SMTP server, port, sender username, and sender password/app-password.
6. Apply/save the settings.

The **sender** can be any mailbox you control that allows SMTP. The **recipient** remains `farhanshoffi@moe.gov.my`.

If the MOE mailbox cannot be used as an SMTP sender because of organisation restrictions, use another sender mailbox (for example, a personal Gmail with an app password) and keep the recipient as the MOE address.

## 2. Create the cBot

1. Open the **Algo** section in cTrader Desktop.
2. Create a new blank C# cBot named `CasioRegimeRouterSignal`.
3. Replace the generated code with the contents of `ctrader/CasioRegimeRouterSignal.cs`.
4. Click **Build**.
5. The build must complete successfully before starting an instance.

## 3. Start on XAUUSD M15

1. Open **XAUUSD**.
2. Set the chart to **15 minutes**.
3. Add/start `CasioRegimeRouterSignal` on that chart.
4. Keep these initial parameters:
   - Recipient Email: `farhanshoffi@moe.gov.my`
   - Sender Email: the same address configured in cTrader SMTP settings
   - Send Test Email On Start: `true`
   - Email Exit Notice: `false`
   - Risk %: `5`
   - Strong H4 ADX: `18`
   - Agreement Window Bars: `2`
   - Signal Only: `true`

The bot refuses to run on a symbol other than XAUUSD or a timeframe other than M15.

## 4. Verify the test email

When the cBot starts, it immediately requests a test email with subject:

`[CASIO RR] FxPro cTrader email test`

Check `farhanshoffi@moe.gov.my`, including Spam/Junk.

Once the test arrives, set **Send Test Email On Start = false** so restarts do not create unnecessary test messages.

If the email does not arrive, check the cBot Log first. Email delivery depends on the SMTP settings configured in cTrader.

## 5. What a real signal email contains

A live accepted Regime Router setup emails:

- LONG or SHORT
- TREND or MIXED router mode
- selected technique
- entry estimate
- stop loss
- take profit
- 2R / 3R / 4R target
- 5% risk model
- approximate position size in lots and units
- H1 bias
- H4 bias
- H4 ADX
- recent long/short technique agreement

Example subject:

`[CASIO RR] XAUUSD LONG | TREND | M15-0591 MTF`

The entry estimate uses the live FxPro quote immediately after the M15 signal candle closes. That is the live equivalent of the next-bar-open execution assumption used in research.

## 6. One virtual portfolio position at a time

The bot maintains a shadow/virtual trade after emailing an entry. It will not emit another entry until that virtual setup reaches its SL or TP.

This preserves the same high-level portfolio rule used in the Regime Router research: one shared account, one active routed trade at a time.

If SL and TP are both touched inside the same completed M15 candle, the bot treats it as a stop first, matching the conservative backtest assumption.

`Email Exit Notice` is off by default. Turn it on if you also want virtual STOP/TARGET emails.

## 7. TradingView remains separate

Keep `tradingview/casio_regime_router_dashboard_v1.pine` for:

- visual dashboard
- Entry / SL / TP chart levels
- Strategy Tester
- historical comparison

No TradingView technical alert is required for email delivery.

## 8. Running continuously

First verify the cBot and email locally on cTrader Desktop.

For continuous operation:

- Local cTrader: the app/computer must stay running.
- VPS: run cTrader continuously on a VPS.
- cTrader Cloud: cBots can run 24/7, but verify the test email from a cloud instance before relying on cloud email delivery in your account/environment.

Do not assume email is working continuously until the test email has been received from the exact execution mode you intend to use.

## Important separation

The live cBot and TradingView may print slightly different values because they can use different XAUUSD feeds. For live email signals, the cBot uses the actual FxPro/cTrader feed it is attached to, which is preferable for execution decisions on that FxPro account.
