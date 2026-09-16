import requests
import time
import json

BASE_URL = "https://catrader.site"

print("=== Testing Live Production Deployment on catrader.site ===")

s = requests.Session()

# 1. Login to obtain session cookie
print("\n[1] Logging into CA Trader...")
login_payload = {"username": "admin", "password": "password"}
try:
    r_login = s.post(f"{BASE_URL}/api/auth/login", json=login_payload, timeout=10)
    print(f"Login response status: {r_login.status_code}")
    if r_login.status_code != 200:
        # Check if auth works with default user or check /api/auth/me
        print("Login detail:", r_login.text[:200])
except Exception as e:
    print("Login error:", e)

# 2. Test Recommendation Refresh endpoint: /api/recommendations/NIFTY
print("\n[2] Testing Recommendation Endpoint (/api/recommendations/NIFTY)...")
t0 = time.time()
try:
    r_rec = s.get(f"{BASE_URL}/api/recommendations/NIFTY", timeout=10)
    dt_rec = (time.time() - t0) * 1000
    print(f"Status: {r_rec.status_code} in {dt_rec:.1f}ms")
    if r_rec.status_code == 200:
        data = r_rec.json()
        print("  Direction:", data.get("direction"))
        print("  Contract:", data.get("contract"))
        print("  Entry:", data.get("entry"))
        print("  Stop Loss:", data.get("stop_loss"))
        print("  Target:", data.get("target"))
        print("  Confidence:", data.get("confidence"))
    else:
        print("Error response:", r_rec.text[:200])
except Exception as e:
    print("Error calling recommendations:", e)

# 3. Test CA AI Chart Suggestions endpoint: /api/analysis/chart-ai-suggestions/NIFTY
print("\n[3] Testing CA AI Chart Suggestions Endpoint (/api/analysis/chart-ai-suggestions/NIFTY)...")
t0 = time.time()
try:
    r_sug = s.get(f"{BASE_URL}/api/analysis/chart-ai-suggestions/NIFTY?timeframe=5m&days=5", timeout=10)
    dt_sug = (time.time() - t0) * 1000
    print(f"Status: {r_sug.status_code} in {dt_sug:.1f}ms")
    if r_sug.status_code == 200:
        data = r_sug.json()
        trendlines = data.get("trendlines", [])
        horiz = data.get("horizontal_levels", [])
        indics = data.get("indicators", [])
        print(f"  Trendlines count: {len(trendlines)}")
        print(f"  Horizontal levels: {len(horiz)}")
        print(f"  Indicators count: {len(indics)}")
        if trendlines:
            print("  Top Trendline:", trendlines[0].get("name"), trendlines[0].get("description"))
        if indics:
            print("  Top Indicator:", indics[0].get("name"), indics[0].get("reason"))
    else:
        print("Error response:", r_sug.text[:200])
except Exception as e:
    print("Error calling chart-ai-suggestions:", e)

# 4. Test Ask CA AI Chat endpoint: /api/ai/chat
print("\n[4] Testing Ask CA AI Endpoint (/api/ai/chat)...")
t0 = time.time()
chat_payload = {
    "message": "What is the active trade setup on NIFTY, and can you switch to a PE put option?",
    "symbol": "NIFTY",
    "current_setup": {
        "direction": "BUY",
        "contract": "NIFTY 23400 CE",
        "entry": 115.0,
        "stop_loss": 95.0,
        "target": 155.0
    }
}
try:
    r_chat = s.post(f"{BASE_URL}/api/ai/chat", json=chat_payload, timeout=12)
    dt_chat = (time.time() - t0) * 1000
    print(f"Status: {r_chat.status_code} in {dt_chat:.1f}ms")
    if r_chat.status_code == 200:
        data = r_chat.json()
        print("  Model:", data.get("model"))
        print("  Has updated_setup:", data.get("updated_setup") is not None)
        print("  AI Response Preview:\n" + ("-"*40))
        msg = data.get("message") or data.get("reply") or ""
        print(msg[:350] + ("..." if len(msg) > 350 else ""))
        print("-" * 40)
    else:
        print("Error response:", r_chat.text[:200])
except Exception as e:
    print("Error calling ai chat:", e)

print("\n=== Live Test Complete ===")

