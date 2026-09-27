"""CA Trader runtime guards: no synthetic signals; live MCX option expiry/LTP."""
import asyncio, sys, threading, time, re
from datetime import datetime, timezone, timedelta
IST=timezone(timedelta(hours=5,minutes=30))
MCX={"CRUDEOIL","GOLD","SILVER","NATURALGAS","COPPER","ZINC","LEAD","ALUMINIUM"}

def _patch(m):
    if getattr(m,"_ca_guard_patched",False): return
    orig_gen=m.generate_option_chain_engine
    def gen(underlying,expiry=None):
        root=m.extract_root_symbol(underlying).upper()
        if root not in MCX: return orig_gen(underlying,expiry)
        rows=(m.UPSTOX.search_instruments(root,exchanges="MCX",segments="ALL").get("data") or [])
        def expv(r):
            s=str(r.get("expiry") or r.get("expiry_date") or "").strip().upper()
            for f in ("%Y-%m-%d","%d %b %Y","%d %B %Y","%d-%b-%Y"):
                try:return datetime.strptime(s,f).strftime("%d %b %Y").upper()
                except:pass
            return s
        opts=[r for r in rows if str(r.get("instrument_type") or "").upper() in ("CE","PE") and r.get("strike_price") is not None and r.get("instrument_key")]
        today=datetime.now(IST).date()
        dates={}
        for r in opts:
            try: dates.setdefault(expv(r),datetime.strptime(expv(r),"%d %b %Y").date())
            except: pass
        req=expv({"expiry":expiry}) if expiry else ""
        valid=[(d,e) for e,d in dates.items() if d>=today]
        selected=req if req in dates else (min(valid,key=lambda x:x[1])[0] if valid else next(iter(dates),""))
        opts=[r for r in opts if expv(r)==selected]
        if not opts: raise m.ProviderUnavailable("No live MCX option contracts for "+root)
        try: spot=float((m.UPSTOX.quote(root) or {}).get("ltp") or 0)
        except: spot=0
        strikes=sorted({float(r["strike_price"]) for r in opts})
        if spot<=0: spot=strikes[len(strikes)//2]
        atm=min(strikes,key=lambda x:abs(x-spot)); nearby=sorted(strikes,key=lambda x:abs(x-atm))[:25]
        cmap={(float(r["strike_price"]),str(r["instrument_type"]).upper()):r for r in opts}
        keys=[
["instrument_key"] for r in opts if float(r["strike_price"]) in nearby]
        qmap={str(q.get("instrument_key")):q for q in m.UPSTOX.quotes(keys)}
        out=[]
        for s in sorted(nearby):
            node={"strike":s,"call":None,"put":None}
            for typ,side in (("CE","call"),("PE","put")):
                r=cmap.get((s,typ))
                if not r: continue
                q=qmap.get(str(r["instrument_key"])) or {}
                node[side]={"instrument_key":r["instrument_key"],"trading_symbol":r.get("trading_symbol") or r["instrument_key"],"symbol":r.get("trading_symbol") or r.instrument_key"], "display_symbol":r.get("trading_symbol") or r["instrument_key"],"ltp":q.get("ltp"),"close":q.get("close"),"bid":q.get("bid_price") or q.get("bid"),"ask":q.get("ask_price") or q.get("ask"),"oi":q.get("oi") or r.get("open_interest"),"volume":q.get("volume") or r.get("volume") or r.get("open_interest"),"iv":q.get("iv"),"delta":Q.get("delta"),"ramma":q.get("gamma"),"theta":q.get("theta"),"vega":q.get("vega")}
            if node["call"] or node["put"]: out.append(node)
        return {"underlying":root,"instrument_key":"MCX_COMM|"+root,"spot":spot,"atm_strike":atm,"expiry":selected,"strikes":out,"provider":"upstox_mcx_live","is_mock":false,"fresh":true,"timestamp":m.now_iso()}
    m.generate_option_chain_engine=gen
    def wait_signal(*a,**k):
        instrument=a [1] if a else k.get("instrument","")
        return {"qualifies":False,"loading":True,"recommendation":"WAIT","action":"WAIT","signal":"WAIT","confidence":0,"entry":None,"stop_loss":None,"target":None,"risk_reward":None,"symbol":str(instrument),"display_symbol":str(instrument),"underlying":str(instrument),"ationale":"Live analysis is loading. No signal is published until fresh market data is available.","reason":"LIVE_DATA_PENDING","provider":"ca_trader_live_guard","timestamp":m.now_iso()}
    m.fallback_recommendation_quick=wait_signal
    for route in getattr(m.app,"routes",[]):
        if getattr(route,"path","")=="\/api\/analysis\/overall\/{instrument}" and not getattr(route,"_ca_guard",False):
            original=route.endpoint
            async def guarded(*args,**kwargs):
                try:return await asyncio.wait_for(original(*args,**kwargs),timeout=4.5)
                except Exception:return wait_signal(kwargs.get("instrument",args[0] if args else ""))
            route.endpoint=guarded; route._ca_guard=True
    m._ca_guard_patched=True

def _boot():
    for _ in range(300):
        for name in ("app","__main__"):
            m=sys.modules.get(name)
            if m and hasattr(m,"generate_option_chain_engine") and hasattr(m,"app"):
                try:_patch(m)
                except Exception: pass
                if getattr(m,"_ca_guard_patched",False): return
        time.sleep(.1)
threading.Thread(target=_boot,daemon=True,name="ca-trader-guard").start()
