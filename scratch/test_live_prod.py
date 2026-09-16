import urllib.request, json, ssl

def test_production():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("=== Testing Production API (https://catrader.site) ===")

    # Test 1: Macro factors (Dow, S&P 500, Gift Nifty, Crude, etc.)
    try:
        req = urllib.request.Request('https://catrader.site/api/market/macro-factors', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("\n[1] /api/market/macro-factors:")
            print("  Data state:", data.get('data_state'))
            print("  Gift Nifty:", data.get('gift_nifty', {}).get('level'), "Change:", data.get('gift_nifty', {}).get('pct'), "%")
            us = data.get('us_markets', {})
            print("  Dow Jones:", us.get('dow', {}).get('level'), "Prev close:", us.get('dow', {}).get('prev_close'), "Pct:", us.get('dow', {}).get('pct'), "%")
            print("  S&P 500:", us.get('sp500', {}).get('level'), "Prev close:", us.get('sp500', {}).get('prev_close'), "Pct:", us.get('sp500', {}).get('pct'), "%")
            print("  Nasdaq:", us.get('nasdaq', {}).get('level'), "Prev close:", us.get('nasdaq', {}).get('prev_close'))
            print("  Macro drivers:")
            for d in data.get('macro_drivers', []):
                print(f"    - {d.get('factor')}: {d.get('level')} (Prev: {d.get('prev_close')}, Change: {d.get('change')})")
    except Exception as e:
        print("  Error testing macro factors:", e)

    # Test 2: Terminal HTML served
    try:
        req = urllib.request.Request('https://catrader.site/terminal', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            html = resp.read().decode('utf-8')
            print("\n[2] /terminal HTML verification:")
            print("  Contains panel-reco:", 'id="panel-reco"' in html)
            print("  Contains panel-dashboard:", 'id="panel-dashboard"' in html)
            print("  Contains chartAiSuggestBtnMobile:", 'id="chartAiSuggestBtnMobile"' in html)
            print("  Contains calcPureBsGreeks:", 'calcPureBsGreeks' in html)
            print("  Has 'LOCAL FALLBACK':", 'LOCAL FALLBACK' in html)
    except Exception as e:
        print("  Error fetching terminal:", e)

if __name__ == '__main__':
    test_production()

