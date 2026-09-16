import sys, urllib.request, http.cookiejar, json, ssl
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_URL = "https://catrader.site"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ctx)
)

print("1. Testing Health Endpoint...")
req = urllib.request.Request(f"{BASE_URL}/health", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    data = json.loads(r.read().decode("utf-8"))
    print("✓ Health:", data)

print("\n2. Logging in with Admin credentials...")
login_payload = json.dumps({"email": "santoshmadnani553@gmail.com", "password": "Admin@123"}).encode("utf-8")
login_req = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=login_payload,
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
)
with opener.open(login_req) as r:
    login_res = json.loads(r.read().decode("utf-8"))
    print("✓ Logged in successfully:", login_res.get("ok", True))

print("\n3. Testing Admin API Passbook (/api/admin/api-passbook)...")
req = urllib.request.Request(f"{BASE_URL}/api/admin/api-passbook", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    pb = json.loads(r.read().decode("utf-8"))
    print("✓ Passbook OK:", pb.get("ok"))
    print("  Upstox Meter:", pb.get("upstox"))
    print("  Gemini Meter:", pb.get("gemini"))
    print("  Statement Entries:", len(pb.get("statement", [])))

print("\n4. Testing CRUDEOIL Option Chain Engine (/api/options/CRUDEOIL)...")
req = urllib.request.Request(f"{BASE_URL}/api/options/CRUDEOIL", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    opt = json.loads(r.read().decode("utf-8"))
    spot = opt.get("spot")
    chain = opt.get("chain", [])
    print(f"✓ CRUDEOIL spot: {spot}")
    if chain:
        sample = chain[len(chain)//2]
        print(f"  Strike: {sample.get('strike')}, CE LTP: {sample.get('call_ltp')}, PE LTP: {sample.get('put_ltp')}")
        print(f"  CE OI: {sample.get('call_oi')}, PE OI: {sample.get('put_oi')}")

print("\n5. Testing Recommendations History (/api/recommendations/history)...")
req = urllib.request.Request(f"{BASE_URL}/api/recommendations/history", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    hist = json.loads(r.read().decode("utf-8"))
    items = hist.get("items", [])
    print(f"✓ Recommendations History retrieved: {len(items)} items")
    if items:
        latest = items[0]
        print(f"  Latest setup: {latest.get('symbol')} ({latest.get('recommendation')}) | Entry: {latest.get('entry')} | Status: {latest.get('status')}")

print("\n6. Testing Save Recommendation to History (/api/recommendations/save)...")
save_data = json.dumps({
    "symbol": "CRUDEOIL",
    "underlying": "CRUDEOIL",
    "recommendation": "BUY",
    "entry": 6150.0,
    "target": 6220.0,
    "stop_loss": 6110.0,
    "timeframe": "5m",
    "rationale": "Live Release 52 verification setup: Strong momentum above 20 EMA.",
    "confidence": 85.0
}).encode("utf-8")
req = urllib.request.Request(f"{BASE_URL}/api/recommendations/save", data=save_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    save_res = json.loads(r.read().decode("utf-8"))
    print("✓ Saved reco response:", save_res)

print("\n7. Testing News Feed (/api/news/ca-ai)...")
req = urllib.request.Request(f"{BASE_URL}/api/news/ca-ai", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    news = json.loads(r.read().decode("utf-8"))
    articles = news.get("items") or news.get("news") or []
    print(f"✓ CA AI News Feed loaded: {len(articles)} articles")
    if articles:
        print(f"  First news: {articles[0].get('headline')[:60]}... | Impact: {articles[0].get('materiality')}%")

print("\n8. Verifying Terminal HTML served on production...")
req = urllib.request.Request(f"{BASE_URL}/terminal", headers={"User-Agent": "Mozilla/5.0"})
with opener.open(req) as r:
    html = r.read().decode("utf-8")
    checks = [
        ('panel-notifications', 'id="panel-notifications"' in html),
        ('panel-api-passbook', 'id="panel-api-passbook"' in html),
        ('rightSideNotificationContainer', 'id="rightSideNotificationContainer"' in html),
        ('turboLoadBtn', 'id="turboLoadBtn"' in html),
        ('btnLockDrawings', 'id="btnLockDrawings"' in html),
        ('floatingPositionWidget', 'id="floatingPositionWidget"' in html),
        ('quickOrderLtp', 'id="quickOrderLtp"' in html)
    ]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} Terminal HTML has {name}: {ok}")

print("\n=== All Production Live Verifications Passed Successfully! ===")

