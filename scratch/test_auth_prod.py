import urllib.request, http.cookiejar, json, ssl

def test_auth():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))

    # Test login with email
    login_data = json.dumps({"email": "santoshmadnani553@gmail.com", "password": "Admin@123"}).encode('utf-8')
    req = urllib.request.Request('https://catrader.site/api/auth/login', data=login_data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("Login response:", data)
    except Exception as e:
        print("Login error:", e)

    # Test /terminal with cookie
    req_term = urllib.request.Request('https://catrader.site/terminal', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req_term) as resp:
            html = resp.read().decode('utf-8')
            print("\n[Terminal Verification]:")
            print("  Status code:", resp.status)
            print("  Contains panel-reco:", 'id="panel-reco"' in html)
            print("  Contains panel-dashboard:", 'id="panel-dashboard"' in html)
            print("  Contains chartAiSuggestBtnMobile:", 'id="chartAiSuggestBtnMobile"' in html)
            print("  Contains calcPureBsGreeks:", 'calcPureBsGreeks' in html)
            print("  Has 'LOCAL FALLBACK':", 'LOCAL FALLBACK' in html)
    except Exception as e:
        print("Terminal fetch error:", e)

    # Test /api/market/macro-factors with cookie
    req_macro = urllib.request.Request('https://catrader.site/api/market/macro-factors', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req_macro) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            print("\n[Macro Factors Verification]:")
            print("  Summary:", d.get('summary'))
            print("  Gift Nifty:", d.get('gift_nifty'))
            print("  US Markets Dow:", d.get('us_markets', {}).get('dow'))
            print("  US Markets S&P:", d.get('us_markets', {}).get('sp500'))
            print("  Macro Drivers:")
            for m in d.get('macro_drivers', []):
                print(f"    - {m.get('factor')}: Level={m.get('level')} Prev={m.get('prev_close')} Chg={m.get('change')} Source={m.get('source')}")
    except Exception as e:
        print("Macro fetch error:", e)

    # Test /api/news/unified with cookie
    req_news = urllib.request.Request('https://catrader.site/api/news/unified?symbol=NIFTY&limit=60', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req_news) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            events = d.get('events', [])
            print(f"\n[News Verification]: Found {len(events)} events for NIFTY")
            for ev in events[:3]:
                print(f"  - [{ev.get('source')}] {ev.get('event')[:70]}...")
    except Exception as e:
        print("News fetch error:", e)

    # Test /api/recommendations/history with cookie
    req_hist = urllib.request.Request('https://catrader.site/api/recommendations/history', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req_hist) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            items = d.get('items', [])
            print(f"\n[Recommendations History Verification]: Found {len(items)} history records")
    except Exception as e:
        print("History fetch error:", e)

if __name__ == '__main__':
    test_auth()

