from __future__ import annotations

import numpy as np
import pandas as pd

BIG = 1e9


def rolling_max(a, n): return pd.Series(a).rolling(n, min_periods=1).max().to_numpy()
def rolling_min(a, n): return pd.Series(a).rolling(n, min_periods=1).min().to_numpy()

def bars_last(e):
    out=np.full(len(e),np.nan); last=None
    for i,v in enumerate(e):
        if v: last=i
        if last is not None: out[i]=i-last
    return out

def value_when(e, x): return pd.Series(np.where(e,x,np.nan)).ffill().to_numpy()

def ref(a,n=1,fill=np.nan):
    out=np.full(len(a),fill,dtype=float if np.asarray(a).dtype!=bool else bool)
    if n: out[n:]=a[:-n]
    else: out[:]=a
    return out

def vector_swing(h,l,n):
    hc=ref(h,n)>rolling_max(h,n)
    lc=(ref(l,n)<rolling_min(l,n)) & ~hc
    pha=np.nan_to_num(ref(bars_last(hc),1),nan=BIG)
    pla=np.nan_to_num(ref(bars_last(lc),1),nan=BIG)
    prev_bear=pha<=pla
    top=hc & ~prev_bear
    bot=lc & prev_bear
    tv=ref(h,n); bv=ref(l,n)
    return top,bot,value_when(top,tv),value_when(bot,bv)

def crossover(x,y): return (x>y)&(ref(x,1)<=ref(y,1))
def crossunder(x,y): return (x<y)&(ref(x,1)>=ref(y,1))

def once(raw,pivot):
    age=np.nan_to_num(bars_last(pivot),nan=BIG)
    prev_raw=np.nan_to_num(ref(bars_last(raw),1),nan=BIG)
    return raw & (age<=prev_raw)

def classify(up,dn):
    anye=up|dn
    d=np.where(dn,-1,np.where(up,1,np.nan))
    prev=np.nan_to_num(ref(value_when(anye,d),1),nan=0)
    uch=up&(prev==-1); ub=up&~uch
    after=np.where(up,1,prev)
    dch=dn&(after==1); db=dn&~dch
    return ub,uch,db,dch

def vector_engine(o,h,l,c,swing_len):
    st,sb,sth,sbl=vector_swing(h,l,swing_len)
    it,ib,ith,ibl=vector_swing(h,l,5)
    iup=once(crossover(c,ith)&~np.isnan(ith)&~np.isnan(sth)&(ith!=sth),it)
    idn=once(crossunder(c,ibl)&~np.isnan(ibl)&~np.isnan(sbl)&(ibl!=sbl),ib)
    sup=once(crossover(c,sth),st); sdn=once(crossunder(c,sbl),sb)
    return (st,sb,it,ib,iup,idn,sup,sdn,*classify(iup,idn),*classify(sup,sdn))

class Pivot:
    def __init__(self): self.level=np.nan; self.crossed=False
class Trend:
    def __init__(self): self.bias=0
class LegEngine:
    def __init__(self,n): self.n=n; self.leg=0; self.high=Pivot(); self.low=Pivot()
    def update(self,i,h,l):
        n=self.n
        newh=False; newl=False
        if i>=n:
            # Pine ta.highest(n) / ta.lowest(n): current and preceding n-1 bars.
            newh=h[i-n]>np.max(h[max(0,i-n+1):i+1])
            newl=l[i-n]<np.min(l[max(0,i-n+1):i+1])
        old=self.leg
        if newh: self.leg=0
        elif newl: self.leg=1
        top=(self.leg==0 and old!=0)
        bot=(self.leg==1 and old!=1)
        if top:
            self.high.level=h[i-n]; self.high.crossed=False
        if bot:
            self.low.level=l[i-n]; self.low.crossed=False
        return top,bot

def scalar_engine(o,h,l,c,swing_len):
    n=len(c); sw=LegEngine(swing_len); inn=LegEngine(5); stt=Trend(); itt=Trend()
    names=['st','sb','it','ib','iup','idn','sup','sdn','iub','iuch','idb','idch','sub','such','sdb','sdch']
    out={k:np.zeros(n,bool) for k in names}
    for i in range(n):
        out['st'][i],out['sb'][i]=sw.update(i,h,l)
        out['it'][i],out['ib'][i]=inn.update(i,h,l)
        pc=c[i-1] if i else np.nan
        # Internal bullish
        bull_extra=not np.isnan(inn.high.level) and not np.isnan(sw.high.level) and inn.high.level!=sw.high.level
        if not np.isnan(inn.high.level) and c[i]>inn.high.level and (i==0 or pc<=inn.high.level) and not inn.high.crossed and bull_extra:
            tag_ch=itt.bias==-1; out['iup'][i]=True; out['iuch' if tag_ch else 'iub'][i]=True
            inn.high.crossed=True; itt.bias=1
        bear_extra=not np.isnan(inn.low.level) and not np.isnan(sw.low.level) and inn.low.level!=sw.low.level
        if not np.isnan(inn.low.level) and c[i]<inn.low.level and (i==0 or pc>=inn.low.level) and not inn.low.crossed and bear_extra:
            tag_ch=itt.bias==1; out['idn'][i]=True; out['idch' if tag_ch else 'idb'][i]=True
            inn.low.crossed=True; itt.bias=-1
        if not np.isnan(sw.high.level) and c[i]>sw.high.level and (i==0 or pc<=sw.high.level) and not sw.high.crossed:
            tag_ch=stt.bias==-1; out['sup'][i]=True; out['such' if tag_ch else 'sub'][i]=True
            sw.high.crossed=True; stt.bias=1
        if not np.isnan(sw.low.level) and c[i]<sw.low.level and (i==0 or pc>=sw.low.level) and not sw.low.crossed:
            tag_ch=stt.bias==1; out['sdn'][i]=True; out['sdch' if tag_ch else 'sdb'][i]=True
            sw.low.crossed=True; stt.bias=-1
    return tuple(out[k] for k in names)

def main():
    for sl in (10,20,50,100):
        for seed in range(100):
            rng=np.random.default_rng(300000+sl*1000+seed); n=2400
            close=100*np.exp(np.cumsum(rng.normal(0,0.014,n)))
            op=np.r_[close[0],close[:-1]*(1+rng.normal(0,0.002,n-1))]
            sp=np.abs(rng.normal(0.008,0.004,n)); h=np.maximum(op,close)*(1+sp); l=np.minimum(op,close)*(1-sp)
            v=vector_engine(op,h,l,close,sl); s=scalar_engine(op,h,l,close,sl)
            names=['st','sb','it','ib','iup','idn','sup','sdn','iub','iuch','idb','idch','sub','such','sdb','sdch']
            for name,a,b in zip(names,v,s):
                if not np.array_equal(a,b):
                    idx=np.flatnonzero(a!=b)[0]
                    raise AssertionError(f'{name} mismatch swing={sl} seed={seed} first={idx}')
    print('LuxAlgo pivot/crossed/trend structure state: PASS (400 randomized histories)')
if __name__=='__main__': main()
