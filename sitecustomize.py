
import asyncio
import sys
import threading
import time
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
MCX_ROOTS = {"CRUDEOIL","GOLD","SILVER","NATURALGAS","COPPER","ZINC","LEAD","ALUMINIUM"}

def _patch(mod):
    if getattr(mod, "_ca_runtime_guard", False):
        return
    original_chain = mod.generate_option_chain_engine

    def live_chain(underlying, expiry=None):
        root = mod.extract_root_symbol(underlying).upper()
        if root not in MCX_ROOTS:
            return original_chain(underlying, expiry)
        rows = (mod.UPSTOX.search_instruments(root, exchanges="MCX", segments="ALL").get("data") or [])
        def norm_exp(row):
            value = str(row.get("expiry") or row.get("expiry_date") or "").strip().upper()
            for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d-%b-%Y"):
                try:
                    return datetime.strptime(value, fmt).strftime("%d %b %Y").upper()
                except Exception:
                    pass
            return value
        options = [r for r in rows if str(r.get("instrument_type") or "").upper() in {"CE","PE"}
                   and r.get("strike_price") is not None and r.get("instrument_key")]
        if not options:
            raise mod.ProviderUnavailable(f"No live MCX options returned for {root}")
        today = datetime.now(IST).date()
        dates = {}
        for row in options:
            exp = norm_exp(row)
            try:
                dates[exp] = datetime.strptime(exp, "%d %b %Y").date()
            except Exception:
                pass
        requested = str(expiry or "").strip().upper()
        if requested:
            try:
                requested = datetime.strptime(requested, "%Y-%m-%d").strftime("%d %b %Y").upper()
            except Exception:
                pass
        future = [(exp, day) for exp, day in dates.items() if day >= today]
        selected = requested if requested in dates else min(future, key=lambda x: x[1])[0]
        options = [r for r in options if norm_exp(r) == selected]
        strikes = sorted({float(r["strike_price"]) for r in options})
        try:
            spot = float((mod.UPSTOX.quote(root) or {}).get("ltp") or 0)
        except Exception:
            spot = 0
        if spot <= 0:
            spot = strikes[len(strikes)//2]
        atm = min(strikes, key=lambda x: abs(x - spot))
        nearby = sorted(strikes, key=lambda x: abs(x - atm))[:25]
        by_contract = {(float(r["strike_price"]), str(r["instrument_type"]).upper()): r for r in options}
        keys = [r["instrument_key"] for r in options if float(r["strike_price"]) in nearby]
        quotes = {str(q.get("instrument_key")): q for q in mod.UPSTOX.quotes(keys)}
        result = []
        for strike in sorted(nearby):
            node = {"strike": strike, "call": None, "put": None}
            for typ, side in (("CE","call"), ("PE","put")):
                row = by_contract.get((strike, typ))
                if not row:
                    continue
                q = quotes.get(str(row["instrument_key"])) or {}
                symbol = row.get("trading_symbol") or row["instrument_key"]
                node[side] = {
                    "instrument_key": row["instrument_key"], "trading_symbol": symbol,
                    "symbol": symbol, "display_symbol": symbol, "ltp": q.get("ltp"),
                    "close": q.get("close"), "bid": q.get("bid_price") or q.get("bid"),
                    "ask": q.get("ask_price") or q.get("ask"), "oi": q.get("oi") or row.get("open_interest"),
                    "volume": q.get("volume") or row.get("volume"), "iv": q.get("iv"),
                    "delta": q.get("delta"), "gamma": q.get("gamma"), "theta": q.get("theta"), "vega": q.get("vega")
                }
            if node["call"] or node["put"]:
                result.append(node)
        return {"underlying": root, "instrument_key": f"MCX_COMM|{root}", "spot": spot,
                "atm_strike": atm, "expiry": selected, "strikes": result,
                "provider": "upstox_mcx_live", "is_mock": False, "fresh": True,
                "timestamp": mod.now_iso()}

    mod.generate_option_chain_engine = live_chain

    def wait_signal(instrument, *args, **kwargs):
        return {"qualifies": False, "loading": True, "recommendation": "WAIT",
                "action": "WAIT", "signal": "WAIT", "confidence": 0,
                "entry": None, "stop_loss": None, "target": None, "risk_reward": None,
                "symbol": str(instrument), "display_symbol": str(instrument),
                "underlying": str(instrument),
                "rationale": "Live analysis is loading. No signal is published until fresh market data is available.",
                "reason": "LIVE_DATA_PENDING", "provider": "ca_trader_live_guard",
                "timestamp": mod.now_iso()}
    mod.fallback_recommendation_quick = wait_signal

    for route in getattr(mod.app, "routes", []):
        if getattr(route, "path", "") == "/api/analysis/overall/{instrument}" and not getattr(route, "_ca_guard", False):
            original = route.endpoint
            async def guarded(*args, **kwargs):
                try:
                    return await asyncio.wait_for(original(*args, **kwargs), timeout=4.5)
                except Exception:
                    instrument = kwargs.get("instrument", args[0] if args else "")
                    return wait_signal(instrument)
            route.endpoint = guarded
            route._ca_guard = True
    for route in getattr(mod.app, "routes", []):
        if getattr(route, "path", "") == "/api/options/{underlying}/expiries" and not getattr(route, "_ca_expiry_guard", False):
            original_expiry = route.endpoint
            async def live_expiries(underlying, user=None):
                root = mod.extract_root_symbol(underlying).upper()
                if root not in MCX_ROOTS:
                    return await original_expiry(underlying, user)
                rows = (await asyncio.to_thread(mod.UPSTOX.search_instruments, root, exchanges="MCX", segments="ALL")).get("data") or []
                vals = set()
                today = datetime.now(IST).date()
                for row in rows:
                    if str(row.get("instrument_type") or "").upper() not in {"CE", "PE"}:
                        continue
                    exp = str(row.get("expiry") or row.get("expiry_date") or "").strip().upper()
                    try:
                        day = datetime.strptime(exp, "%Y-%m-%d").date()
                    except Exception:
                        try:
                            day = datetime.strptime(exp, "%d %b %Y").date()
                        except Exception:
                            continue
                    if day >= today:
                        vals.add(day)
                return {"underlying": root, "expiries": [d.strftime("%d %b %Y").upper() for d in sorted(vals)],
                        "provider": "upstox_mcx_live", "timestamp": mod.client_now_iso()}
            route.endpoint = live_expiries
            route._ca_expiry_guard = True
    mod._ca_runtime_guard = True

def _boot():
    for _ in range(300):
        for name in ("app", "__main__"):
            mod = sys.modules.get(name)
            if mod and hasattr(mod, "generate_option_chain_engine") and hasattr(mod, "app"):
                try:
                    _patch(mod)
                except Exception:
                    pass
                if getattr(mod, "_ca_runtime_guard", False):
                    return
        time.sleep(0.1)

threading.Thread(target=_boot, daemon=True, name="ca-trader-runtime-guard").start()
