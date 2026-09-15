import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import json
import base64
import time
import requests
from itsdangerous import TimestampSigner
from app import AUTH_SECRET, db_exec

# 1. Check user
user = db_exec("SELECT id, username, email FROM users ORDER BY id LIMIT 1", fetch="one")
uid = user["id"] if user else 1
print("Using user id:", uid)

# 2. Build signed Starlette session cookie
session_dict = {"user_id": uid, "last_seen": time.time()}
session_json = json.dumps(session_dict).encode("utf-8")
signer = TimestampSigner(AUTH_SECRET)
signed_cookie = signer.sign(base64.b64encode(session_json)).decode("utf-8")

session = requests.Session()
session.cookies.set("session", signed_cookie)

base_url = "http://127.0.0.1:8000"

# Test /api/market/other-factors
r1 = session.get(f"{base_url}/api/market/other-factors?symbol=NIFTY")
print("GET /api/market/other-factors status:", r1.status_code)
if r1.status_code == 200:
    d1 = r1.json()
    print("  Regime:", d1.get("regime", {}).get("current_regime"))
    print("  Archetype:", d1.get("regime", {}).get("strategy_archetype"))
    print("  Breadth Status:", d1.get("market_breadth", {}).get("status"))
    print("  AD Ratio:", d1.get("market_breadth", {}).get("ad_ratio"))
    print("  Sector Leader:", d1.get("sector_rotation", {}).get("leader"))
    print("  ATM IV:", d1.get("volatility_surface", {}).get("atm_iv"), "| Skew:", d1.get("volatility_surface", {}).get("skew"))
    print("  Max Pain:", d1.get("oi_matrix", {}).get("max_pain_strike"), "| Flip:", d1.get("oi_matrix", {}).get("dealer_gamma_flip"))
    print("  Risk Sizing:", d1.get("portfolio_risk", {}).get("recommended_position_sizing"))
    print("  Microstructure:", d1.get("microstructure", {}).get("institutional_velocity"))
else:
    print("  Response:", r1.text[:300])

# Test /api/market/macro-factors
r2 = session.get(f"{base_url}/api/market/macro-factors")
print("GET /api/market/macro-factors status:", r2.status_code)
if r2.status_code == 200:
    d2 = r2.json()
    print("  Score:", d2.get("composite_score"))
    print("  Net Bias:", d2.get("net_bias"))
    print("  Drivers count:", len(d2.get("drivers", [])))
else:
    print("  Response:", r2.text[:300])

# Test /api/analysis/chart-bundle/NIFTY
r3 = session.get(f"{base_url}/api/analysis/chart-bundle/NIFTY?timeframe=5m")
print("GET /api/analysis/chart-bundle/NIFTY status:", r3.status_code)
if r3.status_code == 200:
    d3 = r3.json()
    tech = d3.get("technical_analysis", {})
    print("  Supertrend:", tech.get("supertrend"), "| Direction:", tech.get("supertrend_direction"))
    print("  VWAP:", tech.get("vwap"))
    print("  RSI:", tech.get("rsi"), "| ADX:", tech.get("adx"), "| ATR:", tech.get("atr"))
    print("  Pivot High (Resistance):", tech.get("pivot_high"), "| Low (Support):", tech.get("pivot_low"))
    print("  Breakout:", tech.get("breakout"))
else:
    print("  Response:", r3.text[:300])
"""

res = subprocess.run([
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    remote_host,
    f"docker exec ca-trader python3 -c {subprocess.list2cmdline([script])}"
], capture_output=True, text=True)

print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)

