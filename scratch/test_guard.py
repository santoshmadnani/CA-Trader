import asyncio
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import analysis_overall, db_exec

user = db_exec("SELECT * FROM users LIMIT 1", [], "one") or {"id": 1}

async def test():
    print("=== Testing overall recommendation for NIFTY (Underlying) ===")
    r_nifty = await analysis_overall("NIFTY", "5m", user=user)
    print("NIFTY direction:", r_nifty.get("direction"))
    print("NIFTY entry:", r_nifty.get("entry"))
    print("NIFTY target:", r_nifty.get("target"))
    print("NIFTY SL:", r_nifty.get("stop_loss"))
    print("NIFTY confidence:", r_nifty.get("confidence"))
    print("NIFTY rationale:", r_nifty.get("rationale"))

    print("\n=== Testing overall recommendation for NIFTY 23250 PE (Option) ===")
    r_pe = await analysis_overall("NIFTY 23250 PE", "5m", user=user)
    print("PE recommendation:", r_pe.get("recommendation") or r_pe.get("direction"))
    print("PE qualifies:", r_pe.get("qualifies"))
    print("PE reason:", r_pe.get("reason") or r_pe.get("rationale"))
    print("PE entry:", r_pe.get("entry"))
    print("PE lot_size:", r_pe.get("instrument", {}).get("lot_size"))

asyncio.run(test())

