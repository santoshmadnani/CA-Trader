import urllib.request, http.cookiejar, json, ssl, sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))

# Step 1: Login
login_data = json.dumps({"email": "santoshmadnani553@gmail.com", "password": "Admin@123"}).encode('utf-8')
req_login = urllib.request.Request('https://catrader.site/api/auth/login', data=login_data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
try:
    with opener.open(req_login) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        print(f"Login successful: user={d.get('user', {}).get('name')} email={d.get('user', {}).get('email')}")
except Exception as e:
    print("Login error:", e)
    sys.exit(1)

# Step 2: Fetch /terminal with session cookie
print("\nFetching https://catrader.site/terminal with authenticated session ...")
req_term = urllib.request.Request('https://catrader.site/terminal', headers={'User-Agent': 'Mozilla/5.0'})
with opener.open(req_term) as resp:
    html = resp.read().decode('utf-8')
    print(f"Status: {resp.status}, Content Length: {len(html):,} bytes")

checks = [
    ('ordersAdvisorCard in Orders panel', 'id="ordersAdvisorCard"' in html),
    ('ordersAdvisorPulse indicator', 'id="ordersAdvisorPulse"' in html),
    ('ordersAdvisorVerdict banner', 'id="ordersAdvisorVerdict"' in html),
    ('ordersAdvisorChatBox strategy chat', 'id="ordersAdvisorChatBox"' in html),
    ('ordersPeakPnl metric', 'id="ordersPeakPnl"' in html),
    ('ordersThetaBurn metric', 'id="ordersThetaBurn"' in html),
    ('fpMinBtn onclick toggleFloatingPositionsWidget(event)', 'toggleFloatingPositionsWidget(event)' in html),
    ('toggleFloatingPositionsWidget toggles floatingPosBodyWrapper', 'bodyWrapper.style.display = isFloatingPosMinimized' in html),
    ('adaptive auto-sync 2000ms during trades', 'openList.length > 0 ? 2000 : 5000' in html),
    ('live tick hook for active advisor position', 'window.activeAdvisorPosition.ltp = ltp' in html),
    ('selectAdvisorPositionById row click integration', 'selectAdvisorPositionById' in html),
]

all_passed = True
print("\n=== Release 51 Live Verification Results ===")
for name, ok in checks:
    status = 'PASS' if ok else 'FAIL'
    if not ok: all_passed = False
    print(f"  [{status}] {name}")

# Step 3: Verify /api/positions/advisor endpoint
print("\nTesting /api/positions/advisor API response ...")
req_adv = urllib.request.Request('https://catrader.site/api/positions/advisor', headers={'User-Agent': 'Mozilla/5.0'})
with opener.open(req_adv) as resp:
    adv = json.loads(resp.read().decode('utf-8'))
    print("  Verdict:", adv.get('verdict'))
    print("  Decision:", adv.get('decision'))
    print("  Reason:", adv.get('reason') or adv.get('advice'))
    print("  Theta decay hourly:", adv.get('theta_decay_hourly'))
    print("  Peak PnL:", adv.get('peak_pnl'))
    print("  Current PnL:", adv.get('current_pnl'))

if all_passed:
    print("\n✓ ALL RELEASE 51 VERIFICATIONS PASSED LIVE ON PRODUCTION!")
else:
    print("\n✗ SOME CHECKS FAILED!")
    sys.exit(1)

