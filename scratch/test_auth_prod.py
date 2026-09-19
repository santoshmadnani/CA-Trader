import urllib.request, http.cookiejar, json, ssl

def test_auth():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))

    # Test login with email
    login_data = json.dumps({"email": "santoshmadnani@catrader.site", "password": "Santosh@9340925132#"}).encode('utf-8')
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
            print("  Final URL:", resp.geturl())
            print("  Contains panel-dashboard:", 'id="panel-dashboard"' in html)
            print("  Length of HTML:", len(html))
    except Exception as e:
        print("Terminal fetch error:", e)

if __name__ == '__main__':
    test_auth()

