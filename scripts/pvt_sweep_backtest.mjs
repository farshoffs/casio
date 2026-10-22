#!/usr/bin/env node
/**
 * PVT-inspired Asia sweep / confirmation: month-by-month XAUUSD M5 research.
 *
 * This ports the decision rules of PVT_XAUUSD_Sweep_Confirmation_v1.pine
 * into an auditable approximation for OHLCV historical research.
 * Not a TradingView broker-emulator parity claim.
 *
 * Usage:
 *   node scripts/pvt_sweep_backtest.mjs data/xauusd_m5.csv
 *   node scripts/pvt_sweep_backtest.mjs data/xauusd_m5.csv 2026-09 2026-10
 *
 * Data: UTC bar-open timestamp, open,high,low,close,volume.
 * Input Dukascopy volume differs from FxPro tick volume.
 * Initial equity USD 2,500, 0.25% equity risk/trade, fixed 2.3R target,
 * qty steps of 0.01 oz, assumed USD 0.50/oz round-trip friction.
 */
import { readFileSync } from "node:fs";

function loadBars(path, firstMonth) {
  const csv = readFileSync(path, "utf8");
  const header = csv.indexOf("\n" + firstMonth);
  if (header === -1) throw Error("Warmup month absent in CSV: " + firstMonth);
  return csv.slice(header + 1).trim().split(/\r?\n/).map(line => {
    const [t, o, h, l, c, v] = line.split(",");
    return { t, ms: Date.parse(t), o:+o, h:+h, l:+l, c:+c, v:+v };
  }).filter(b => Number.isFinite(b.ms) && Number.isFinite(b.c));
}
const avg = x => x.reduce((a,b)=>a+b,0)/x.length;

function backtest(bars, config) {
  const useVolume=config.useVolume, useTrend=config.useTrend;
  const cost=config.cost??0.50, riskRate=0.0025, rewardR=2.3;
  let equity=2500, peak=2500, maximumDrawdown=0;
  let atr=NaN, firstTrueRanges=[], previousClose=NaN, volumes=[], relativeVolumes=[];
  let lastHour="", hourClose=NaN, htfCount=0, ema50=NaN, ema200=NaN;
  let trend={close:NaN,fast:NaN,slow:NaN};
  let prevAsia=false, asiaHigh=NaN, asiaLow=NaN, tradesToday=0;
  let setup=null, pendingOrder=null, position=null, bothHit=0;
  const trades=[], stats={acceptedSweeps:0,orders:0};

  function settle(p,b,reason,rawExit) {
    // Synthetic half-cost per fill. A constant USD/oz 0.50 round trip combines
    // spread+slippage for research; adjust for broker, volatility, session.
    const filledEntry=p.entry+(p.side===1?cost/2:-cost/2);
    const filledExit=rawExit+(p.side===1?-cost/2:cost/2);
    const netPricePoints=p.side*(filledExit-filledEntry);
    const grossPricePoints=p.side*(rawExit-p.entry);
    const riskDist=Math.abs(p.signalClose-p.stop);
    const pnl=p.qty*netPricePoints;
    equity+=pnl;
    peak=Math.max(equity,peak);
    maximumDrawdown=Math.max(maximumDrawdown,peak-equity);
    trades.push({
      signal:p.signal, entryTime:p.entryTime, exitTime:b.t,
      side:p.side===1?"LONG":"SHORT",
      entry:Number(p.entry.toFixed(3)), stop:Number(p.stop.toFixed(3)),
      target:Number(p.target.toFixed(3)), exit:Number(rawExit.toFixed(3)),
      qty:Number(p.qty.toFixed(2)), reason,
      grossR:Number((grossPricePoints/riskDist).toFixed(4)),
      netR:Number((netPricePoints/riskDist).toFixed(4)),
      pnl:Number(pnl.toFixed(4)), equity:Number(equity.toFixed(2))
    });
    position=null;
  }

  for (let i=0;i<bars.length;i++) {
    const b=bars[i], hour=Math.floor(b.ms/3600000);
    if (lastHour!=="" && hour!==lastHour && Number.isFinite(hourClose)) {
      // Completed-hour H1 EMA from the previous hour, never current-hour data.
      htfCount++;
      ema50=Number.isNaN(ema50)?hourClose:ema50+2/51*(hourClose-ema50);
      ema200=Number.isNaN(ema200)?hourClose:ema200+2/201*(hourClose-ema200);
      trend={close:hourClose,fast:htfCount>=50?ema50:NaN,slow:htfCount>=200?ema200:NaN};
    }
    lastHour=hour; hourClose=b.c;

    const tr=Math.max(
      b.h-b.l,
      Number.isFinite(previousClose)?Math.abs(b.h-previousClose):0,
      Number.isFinite(previousClose)?Math.abs(b.l-previousClose):0
    );
    if(firstTrueRanges.length<14) {
      firstTrueRanges.push(tr);
      if(firstTrueRanges.length===14) atr=avg(firstTrueRanges);
    } else atr+=(tr-atr)/14;
    previousClose=b.c;

    volumes.push(b.v);
    if(volumes.length>20) volumes.shift();
    const volumeBase=volumes.length===20?avg(volumes):NaN;
    const rvol=volumeBase>0?b.v/volumeBase:NaN;
    const quiet=relativeVolumes.length===6&&relativeVolumes.every(Number.isFinite)
      ?avg(relativeVolumes):NaN;
    relativeVolumes.push(rvol);
    if(relativeVolumes.length>6)relativeVolumes.shift();

    const d=new Date(b.ms),minute=d.getUTCHours()*60+d.getUTCMinutes();
    const inAsia=minute<420;
    const inEntry=(minute>=420&&minute<660)||(minute>=750&&minute<960);
    const newAsia=inAsia&&!prevAsia;
    if(newAsia) {
      asiaHigh=b.h; asiaLow=b.l; tradesToday=0; setup=null;
    } else if(inAsia) {
      asiaHigh=Math.max(asiaHigh,b.h); asiaLow=Math.min(asiaLow,b.l);
    }
    prevAsia=inAsia;

    // Signals are formed at the completed M5 close; orders fill next M5 open.
    if(pendingOrder) {
      position={...pendingOrder, entry:b.o, entryTime:b.t};
      pendingOrder=null;
    }
    if(position) {
      const p=position;
      const hitStop=p.side===1?b.l<=p.stop:b.h>=p.stop;
      const hitTarget=p.side===1?b.h>=p.target:b.l<=p.target;
      if(hitStop||hitTarget) {
        if(hitStop&&hitTarget)bothHit++;
        settle(p,b,hitStop?"stop":"target",hitStop?p.stop:p.target);
      }
    }

    const asiaReady=!inAsia&&Number.isFinite(asiaHigh)&&Number.isFinite(asiaLow)&&asiaHigh>asiaLow;
    const eligible=inEntry&&asiaReady&&!position&&!pendingOrder&&tradesToday<2
      &&equity>0&&Number.isFinite(atr)&&b.t>="2026-09-01";
    const candleRange=Math.max(b.h-b.l,0.01);
    const lowWick=(Math.min(b.o,b.c)-b.l)/candleRange;
    const upWick=(b.h-Math.max(b.o,b.c))/candleRange;
    const body=Math.abs(b.c-b.o)/candleRange;
    const quietOK=!useVolume||(Number.isFinite(quiet)&&quiet<=1.0);
    const sweepVolOK=!useVolume||(Number.isFinite(rvol)&&rvol<=1.5);
    const confirmVolOK=!useVolume||(Number.isFinite(rvol)&&rvol>=1.1);
    const sweptLow=eligible&&b.l<asiaLow-atr*.05&&b.c>asiaLow
      &&b.c<asiaHigh&&lowWick>=.25&&quietOK&&sweepVolOK;
    const sweptHigh=eligible&&b.h>asiaHigh+atr*.05&&b.c<asiaHigh
      &&b.c>asiaLow&&upWick>=.25&&quietOK&&sweepVolOK;

    let orderSubmitted=false;
    if(setup) {
      const elapsed=i-setup.index;
      const expired=elapsed>3||!inEntry||!asiaReady;
      const invalid=setup.side===1?(b.l<setup.extreme||b.c<asiaLow):
        (b.h>setup.extreme||b.c>asiaHigh);
      if(expired||invalid)setup=null;
      else if(elapsed>=1&&eligible&&body>=.45&&confirmVolOK) {
        const longOK=!useTrend||(trend.fast>trend.slow&&trend.close>trend.fast);
        const shortOK=!useTrend||(trend.fast<trend.slow&&trend.close<trend.fast);
        const side=setup.side;
        if((side===1&&longOK&&b.c>setup.trigger&&b.c>b.o)||
           (side===-1&&shortOK&&b.c<setup.trigger&&b.c<b.o)) {
          const stop=side===1?
            Math.min(setup.extreme-atr*.15,b.c-atr*.35):
            Math.max(setup.extreme+atr*.15,b.c+atr*.35);
          const priceRisk=Math.abs(b.c-stop);
          const qty=Math.floor((equity*riskRate/priceRisk)/.01)*.01;
          if(priceRisk<=3*atr&&priceRisk>.01&&qty>=.01) {
            pendingOrder={side,stop,target:b.c+side*priceRisk*rewardR,
              qty,signalClose:b.c,signal:b.t};
            stats.orders++;tradesToday++;setup=null;orderSubmitted=true;
          }
        }
      }
    }
    if(!setup&&!orderSubmitted) {
      if(sweptLow&&!sweptHigh) {
        setup={side:1,index:i,extreme:b.l,trigger:b.h};
        stats.acceptedSweeps++;
      } else if(sweptHigh&&!sweptLow) {
        setup={side:-1,index:i,extreme:b.h,trigger:b.l};
        stats.acceptedSweeps++;
      }
    }
  }
  return {trades,stats,bothHit,openPosition:position!==null||pendingOrder!==null,
    equity:Number(equity.toFixed(4)),maxDrawdown:Number(maximumDrawdown.toFixed(4))};
}
function summarize(trades){
  const wins=trades.filter(t=>t.pnl>0),losses=trades.filter(t=>t.pnl<0);
  const grossProfit=wins.reduce((s,t)=>s+t.pnl,0);
  const grossLoss=losses.reduce((s,t)=>s-t.pnl,0);
  let equity=2500,high=2500,maxDD=0;
  for(const t of trades){equity+=t.pnl;high=Math.max(high,equity);maxDD=Math.max(maxDD,high-equity);}
  return {
    trades:trades.length,wins:wins.length,losses:losses.length,
    winRatePct:trades.length?Number((100*wins.length/trades.length).toFixed(2)):null,
    profitUSD:Number((grossProfit-grossLoss).toFixed(4)),
    expectancyNetR:trades.length?
      Number((trades.reduce((s,t)=>s+t.netR,0)/trades.length).toFixed(4)):null,
    profitFactor:grossLoss?Number((grossProfit/grossLoss).toFixed(4)):null,
    maxDrawdownUSD:Number(maxDD.toFixed(4))
  };
}

const input=process.argv[2]||"data/xauusd_m5.csv";
const month1=process.argv[3]||"2026-09";
const month2=process.argv[4]||"2026-10";
const bars=loadBars(input,"2026-07");
const scopes=[month1,month2];
const variants=[
  ["original",true,true],
  ["without_volume",false,true],
  ["without_trend",true,false],
  ["price_time_only",false,false]
];
const result={
  source:input,lastBar:bars.at(-1)?.t,firstBar:bars[0]?.t,
  coverage:Object.fromEntries(scopes.map(m=>[m,bars.filter(b=>b.t.startsWith(m)).length])),
  settings:{equityUSD:2500,riskPct:0.25,rewardR:2.3,roundTripFrictionUSDperOz:0.5,
    execution:"signal M5 close; next bar open; stop-first same-bar ambiguity",
    h1:"last completed H1 EMA50/EMA200"},
  variants:{}
};
for(const [name,useVolume,useTrend] of variants){
  const run=backtest(bars,{useVolume,useTrend,cost:0.5});
  result.variants[name]={
    diagnostic:run.stats,
    combined:summarize(run.trades.filter(t=>scopes.some(m=>t.entryTime.startsWith(m)))),
    months:Object.fromEntries(scopes.map(m=>[m,summarize(run.trades.filter(t=>t.entryTime.startsWith(m)))])),
    trades:run.trades.filter(t=>scopes.some(m=>t.entryTime.startsWith(m)))
  };
}
console.log(JSON.stringify(result,null,2));
