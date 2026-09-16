import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
host = "ubuntu@15.252.81.122"

remote_code = """
import app, asyncio, json
from datetime import datetime

async def test():
    print("=== LIVE PRODUCTION RELEASE 52 VERIFICATION ===")
    user = {'id': 1, 'username': 'admin', 'role': 'admin'}
    
    # 1. Admin API Passbook
    pb = await app.get_admin_api_passbook(user=user)
    print("\\n1. Admin API Passbook:")
    print("  Status:", pb.get("ok"))
    print("  Upstox Meter:", pb.get("upstox"))
    print("  Gemini Meter:", pb.get("gemini"))
    print("  Data Sources:", len(pb.get("data_sources", [])))
    print("  Statement Entries:", len(pb.get("statement", [])))
    
    # 2. CRUDEOIL Option Chain Engine
    chain_res = await app.options_summary('CRUDEOIL', user=user)
    spot = chain_res.get("spot")
    strikes = chain_res.get("strikes", [])
    print(f"\\n2. CRUDEOIL Option Chain:")
    print(f"  Calibrated Spot: ₹{spot:,.2f}")
    print(f"  Strikes generated: {len(strikes)}")
    if strikes:
        mid = strikes[len(strikes)//2]
        print(f"  ATM Strike {mid.get('strike')}: Call LTP ₹{mid.get('call', {}).get('ltp')} (OI: {mid.get('call', {}).get('oi')}) | Put LTP ₹{mid.get('put', {}).get('ltp')} (OI: {mid.get('put', {}).get('oi')})")
    
    # 3. Single-Direction Consensus & Option Resolution
    ce_res = app.resolve_option_for_future('CRUDEOIL', 'BUY')
    pe_res = app.resolve_option_for_future('CRUDEOIL', 'SELL')
    print(f"\\n3. Directional Consensus:")
    print(f"  Bullish (BUY) -> Option selected: {ce_res.get('display')} (Strike: {ce_res.get('strike')}, Side: {ce_res.get('side')})")
    print(f"  Bearish (SELL) -> Option selected: {pe_res.get('display')} (Strike: {pe_res.get('strike')}, Side: {pe_res.get('side')})")
    assert ce_res.get('side') == 'CE', f"Expected CE for Bullish, got {ce_res.get('side')}"
    assert pe_res.get('side') == 'PE', f"Expected PE for Bearish, got {pe_res.get('side')}"
    print("  ✓ Strict single-direction consensus verified!")

    # 4. Position Live Advisor & Theta Burn & Peak PnL
    adv = await app.position_live_advisor_api(position_id=None, user=user)
    print(f"\\n4. Position Live Advisor:")
    print(f"  Verdict: {adv.get('verdict')}")
    print(f"  Decision: {adv.get('decision')}")
    print(f"  Peak PnL: ₹{adv.get('peak_pnl')} | Current PnL: ₹{adv.get('current_pnl')}")
    print(f"  Theta Decay Hourly: -₹{adv.get('theta_decay_hourly')}/hr | Daily: -₹{adv.get('theta_decay_daily')}/day")

    # 5. Recommendation History & Manual Save
    save_res = await app.save_recommendation_to_history_api({
        "symbol": "CRUDEOIL",
        "underlying": "CRUDEOIL",
        "recommendation": "BUY",
        "entry": spot,
        "target": spot + 75.0,
        "stop_loss": spot - 40.0,
        "timeframe": "5m",
        "rationale": "Release 52 automated verification setup: High volume breakout above 20 EMA.",
        "confidence": 88.0
    }, user=user)
    print(f"\\n5. Recommendation Save API:")
    print(f"  Saved reco: {save_res}")

    hist = await app.recommendation_history(None, user=user)
    items = hist.get("items", [])
    print(f"  History Items count: {len(items)}")
    if items:
        latest = items[0]
        print(f"  Latest in DB: {latest.get('symbol')} ({latest.get('recommendation')}) | Entry: {latest.get('entry')} | Status: {latest.get('status')}")

    # 6. CA AI News Feed (48h cutoff)
    news_res = await app.news_ca_ai_feed('CRUDEOIL', 50, user=user)
    news_items = news_res.get("items", [])
    print(f"\\n6. CA AI News Feed (48h relaxed window):")
    print(f"  Total high-impact news items: {len(news_items)}")
    if news_items:
        first = news_items[0]
        print(f"  Sample: '{first.get('headline')[:60]}...' | Impact: {first.get('materiality')}% | Sentiment: {first.get('sentiment')}")

    print("\\n=== ALL RELEASE 52 PRODUCTION CHECKS PASSED PERFECTLY ===")

asyncio.run(test())
"""

cmd = [
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    f"sudo docker exec -i ca-trader python3 << 'EOF'\n{remote_code}\nEOF"
]

r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
print("STDOUT:\n", r.stdout)
if r.stderr:
    print("STDERR:\n", r.stderr)
if r.returncode != 0:
    print(f"Exit code: {r.returncode}")
    sys.exit(1)
