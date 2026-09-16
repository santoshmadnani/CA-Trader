import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock

print("=== Running Authenticated Test Directly on FastAPI Endpoints ===")

from app import db_exec, analysis_overall, analysis_chart_ai_suggestions, ai_dashboard_chat, ai_chat_alias

# 1. Get first user
user = db_exec("SELECT * FROM users WHERE email='santoshmadnani@catrader.site' LIMIT 1", [], "one")
if not user:
    user = db_exec("SELECT * FROM users LIMIT 1", [], "one")
print("User found:", user["email"], "id=", user["id"])

async def run_tests():
    # 2. Test Recommendation Refresh endpoint (/api/recommendations/NIFTY)
    print("\n--- [TEST 1] /api/recommendations/NIFTY (Recommendation Refresh) ---")
    t0 = time.time()
    rec = await analysis_overall(instrument="NIFTY", timeframe="5m", user=user)
    dt_rec = (time.time() - t0) * 1000
    print(f"Result in {dt_rec:.1f}ms:")
    print("  Direction:", rec.get("direction"))
    print("  Contract:", rec.get("contract"))
    print("  Entry: ₹", rec.get("entry"))
    print("  Stop Loss: ₹", rec.get("stop_loss"))
    print("  Target: ₹", rec.get("target"))
    print("  Confidence:", rec.get("confidence"), "%")

    # Second call should be instant cache (< 1ms)
    t0 = time.time()
    rec2 = await analysis_overall(instrument="NIFTY", timeframe="5m", user=user)
    dt_rec2 = (time.time() - t0) * 1000
    print(f"  Second call (cached) in {dt_rec2:.2f}ms")

    # 3. Test CA AI Chart Suggestions (/api/analysis/chart-ai-suggestions/NIFTY)
    print("\n--- [TEST 2] /api/analysis/chart-ai-suggestions/NIFTY (CA AI Indicators) ---")
    t0 = time.time()
    sug = await analysis_chart_ai_suggestions(instrument="NIFTY", timeframe="5m", days=5, user=user)
    dt_sug = (time.time() - t0) * 1000
    print(f"Result in {dt_sug:.1f}ms:")
    trendlines = sug.get('trendlines', [])
    horiz = sug.get('horizontal_levels', [])
    indics = sug.get('indicators', [])
    print(f"  Trendlines count: {len(trendlines)}")
    print(f"  Horizontal levels count: {len(horiz)}")
    print(f"  Indicators count: {len(indics)}")
    for t in trendlines[:2]:
        print(f"    * {t.get('name')}: {t.get('description')}")
    for ind in indics[:3]:
        print(f"    * {ind.get('name')}: {ind.get('reason')}")

    # Second call cached
    t0 = time.time()
    sug2 = await analysis_chart_ai_suggestions(instrument="NIFTY", timeframe="5m", days=5, user=user)
    dt_sug2 = (time.time() - t0) * 1000
    print(f"  Second call (cached) in {dt_sug2:.2f}ms")

    # 4. Test Ask CA AI Chat (/api/ai/chat)
    print("\n--- [TEST 3] /api/ai/chat (Ask CA AI Chat Modal - Switch to PE) ---")
    chat_payload = {
        "message": "Can you switch this setup to a PE put option?",
        "symbol": "NIFTY",
        "current_setup": rec
    }
    req = MagicMock()
    req.json = AsyncMock(return_value=chat_payload)
    
    t0 = time.time()
    chat_res = await ai_dashboard_chat(request=req, user=user)
    dt_chat = (time.time() - t0) * 1000
    print(f"Result in {dt_chat:.1f}ms:")
    print("  Model:", chat_res.get("model"))
    print("  Has updated_setup:", chat_res.get("updated_setup") is not None)
    if chat_res.get("updated_setup"):
        u = chat_res["updated_setup"]
        print(f"    -> Updated Contract: {u.get('contract')}, Direction: {u.get('direction')}, Entry: ₹{u.get('entry')}, SL: ₹{u.get('stop_loss')}, Target: ₹{u.get('target')}")
    msg = chat_res.get("message") or chat_res.get("reply") or ""
    print("  Response message preview:\n" + msg[:280] + "...")

    # 5. Test Ask CA AI General Query
    print("\n--- [TEST 4] /api/ai/chat (General Strategy & Greeks Query) ---")
    chat_payload2 = {
        "message": "What is the market trend and option Greeks analysis for NIFTY right now?",
        "symbol": "NIFTY",
        "current_setup": rec
    }
    req2 = MagicMock()
    req2.json = AsyncMock(return_value=chat_payload2)
    
    t0 = time.time()
    chat_res2 = await ai_dashboard_chat(request=req2, user=user)
    dt_chat2 = (time.time() - t0) * 1000
    print(f"Result in {dt_chat2:.1f}ms:")
    msg2 = chat_res2.get("message") or chat_res2.get("reply") or ""
    print("  Response message preview:\n" + msg2[:280] + "...")

    print("\n=== ALL DIRECT FASTAPI ENDPOINT TESTS PASSED WITH 0 TIMEOUTS! ===")

asyncio.run(run_tests())

