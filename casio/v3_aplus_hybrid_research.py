from __future__ import annotations

from pathlib import Path
import json, math
import numpy as np
import pandas as pd

from .v3_core import load_m5_csv
from .v3_edge_map import candidate_frame
from .v3_aplus_v2_research import add_regime_features


def _safe(x):
    if isinstance(x, dict): return {str(k):_safe(v) for k,v in x.items()}
    if isinstance(x, list): return [_safe(v) for v in x]
    if isinstance(x,(np.bool_,bool)): return bool(x)
    if isinstance(x,np.integer): return int(x)
    if isinstance(x,(np.floating,float)):
        v=float(x); return v if math.isfinite(v) else None
    if isinstance(x,pd.Timestamp): return x.isoformat()
    return x


def mask_and_target(c: pd.DataFrame, spread: float, slope: float) -> tuple[pd.Series,pd.Series]:
    base_pb=(c.candidate & c.playbook.eq('PULLBACK_CONTINUATION') & c.session.eq('LONDON') & c.extension_atr.le(1.10))
    base_sw=(c.candidate & c.playbook.eq('LIQUIDITY_SWEEP') & c.session.eq('LONDON') & c.body_fraction.ge(.55) & c.body_fraction.lt(.65) & c.efficiency.ge(.20))
    strong=(c.h4_spread_atr.ge(spread) & c.h4_slope20_atr.ge(slope))
    momentum=(c.candidate & c.playbook.eq('PULLBACK_CONTINUATION') & c.session.eq('LONDON') & c.htf_alignment.eq('BOTH_ALIGNED') & c.extension_atr.gt(1.10) & c.extension_atr.le(1.80) & strong)
    mask=base_pb | base_sw | momentum
    # Give only strong-H4 pullbacks 4R. Ordinary A+ entries remain 3R.
    target=pd.Series(np.where(mask & c.playbook.eq('PULLBACK_CONTINUATION') & strong,4.0,3.0),index=c.index)
    return mask,target


def replay(m5:pd.DataFrame,c:pd.DataFrame,spread:float,slope:float,cooldown:int=6,max_hold_bars:int=72,bps:float=1.0)->pd.DataFrame:
    mask,target_series=mask_and_target(c,spread,slope)
    events=[]; active=None; last=-999
    for i,(t,bar) in enumerate(m5.iterrows()):
        if active is not None and i>active['entry_pos']:
            d=active['direction']; ent=active['entry']; risk=active['risk']; stop=active['stop']; tr=active['target_r']
            target=ent+d*risk*tr; lo=float(bar.low); hi=float(bar.high); close=float(bar.close)
            hs=lo<=stop if d==1 else hi>=stop; ht=hi>=target if d==1 else lo<=target; elapsed=i-active['entry_pos']
            if hs and ht: gross=-1.; reason='stop_same_bar'
            elif hs: gross=-1.; reason='stop'
            elif ht: gross=tr; reason=f'target_{tr}r'
            elif elapsed>=max_hold_bars: gross=(close-ent)/risk*d; reason='time_exit'
            else: continue
            cost=(ent*bps/10000.)/risk
            active['exit_time']=t+pd.Timedelta(minutes=5); active['gross_r']=gross; active['net_r']=gross-cost; active['reason']=reason
            events.append({k:v for k,v in active.items() if k!='entry_pos'}); active=None; continue
        if active is not None or i-last<cooldown or not bool(mask.iloc[i]): continue
        row=c.iloc[i]; risk=float(row.risk); ent=float(row.entry); d=int(row.direction); tr=float(target_series.iloc[i])
        if not np.isfinite(risk) or risk<=0 or d==0: continue
        active={'signal_time':t,'entry_time':t+pd.Timedelta(minutes=5),'entry_pos':i,'direction':d,'entry':ent,'risk':risk,'stop':ent-d*risk,'target_r':tr,
                'playbook':row.playbook,'extension_atr':row.extension_atr,'efficiency':row.efficiency,'body_fraction':row.body_fraction,
                'h4_spread_atr':row.h4_spread_atr,'h4_slope20_atr':row.h4_slope20_atr}
        last=i
    return pd.DataFrame(events)


def metrics(tr,a,b):
    if tr.empty: r=pd.Series(dtype=float)
    else:
        tt=pd.to_datetime(tr.entry_time,utc=True); r=pd.to_numeric(tr.loc[(tt>=a)&(tt<b),'net_r'],errors='coerce').dropna()
    if r.empty:return {'trades':0,'wins':0,'losses':0,'win_rate':None,'expectancy_r':None,'profit_factor':None,'avg_win_r':None,'avg_loss_r':None,'max_drawdown_r':None,'trades_per_30d':0.0}
    w=r[r>.05];l=r[r<-.05];gw=float(w.sum());gl=float(-l.sum());curve=r.cumsum();dd=curve.cummax()-curve;days=max((b-a).total_seconds()/86400,1e-9)
    return {'trades':int(len(r)),'wins':int(len(w)),'losses':int(len(l)),'win_rate':float(len(w)*100/len(r)),'expectancy_r':float(r.mean()),'profit_factor':float(gw/gl) if gl>0 else 999.0,'avg_win_r':float(w.mean()) if len(w) else None,'avg_loss_r':float(-l.mean()) if len(l) else None,'max_drawdown_r':float(dd.max()),'trades_per_30d':float(len(r)*30/days)}


def run(data_path='data/xauusd_m5.csv',output_dir='reports/v3-aplus-hybrid'):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);m5=load_m5_csv(data_path);c=add_regime_features(m5,candidate_frame(m5))
    start=m5.index.min()+pd.Timedelta(days=30);finish=m5.index.max()+pd.Timedelta(minutes=5);cut=start+(finish-start)*.70
    rows=[]
    for name,spread,slope in [('HYBRID03',.30,.10),('HYBRID05',.50,.15),('HYBRID07',.70,.15),('HYBRID10',1.0,.20)]:
        tr=replay(m5,c,spread,slope);tr.to_csv(out/f'{name.lower()}_trades.csv',index=False)
        for sample,a,b in [('EARLY70',start,cut),('LATE30',cut,finish),('FULL',start,finish)]: rows.append({'profile':name,'sample':sample,**metrics(tr,a,b)})
    frame=pd.DataFrame(rows);frame.to_csv(out/'metrics.csv',index=False)
    summary={'data':{'rows':len(m5),'start':m5.index.min(),'end':m5.index.max(),'cut':cut},'results':rows,'auto_deploy':False,'note':'Research only. Dynamic 3R/4R target and strong-H4 extended pullback branch. Live unchanged.'}
    (out/'summary.json').write_text(json.dumps(_safe(summary),indent=2),encoding='utf-8');(out/'REPORT.md').write_text('# CASIO A+ Hybrid\n\n```text\n'+frame.to_string(index=False)+'\n```\n',encoding='utf-8')
    return summary


def main():
    import argparse;p=argparse.ArgumentParser();p.add_argument('--data',default='data/xauusd_m5.csv');p.add_argument('--output',default='reports/v3-aplus-hybrid');a=p.parse_args();print(json.dumps(_safe(run(a.data,a.output)),indent=2))
if __name__=='__main__':main()
