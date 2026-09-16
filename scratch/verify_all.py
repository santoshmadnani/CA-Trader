import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app
import json
import base64
import time
import urllib.request
from itsdangerous import TimestampSigner

signer = TimestampSigner(str(app.AUTH_SECRET))
session_dict = {'user_id': 1, 'last_seen': time.time(), 'remember_me': True}
data = base64.b64encode(json.dumps(session_dict).encode('utf-8'))
cookie_val = signer.sign(data).decode('utf-8')
def verify_all():
    print("=== Verification Suite ===")
    
    # 1. Check app.py compilation & import
    import app
    print("app.py imported successfully!")

# Wait for server ready
for _ in range(10):
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/')
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print('Server is up and responsive!')
                break
    except Exception:
        time.sleep(0.5)
    # 2. Check global market quotes
    quotes = app.fetch_global_market_quotes()
    print(f"Global quotes fetched: {len(quotes)} symbols")
    for k, v in quotes.items():
        print(f"  {k:10s} : Price={v.get('price')} Prev={v.get('prev_close')} Chg={v.get('change')} ({v.get('pct')}%)")

# Test 1: CA AI News feed
req_news = urllib.request.Request('http://127.0.0.1:8000/api/news/ca-ai-feed?symbol=RELIANCE&mode=all')
req_news.add_header('Cookie', f'session={cookie_val}')
with urllib.request.urlopen(req_news, timeout=10) as r:
    d = json.loads(r.read().decode('utf-8'))
    items = d.get('items') or d.get('events') or []
    print(f'1. CA AI News Feed Test: {len(items)} items returned')
    for i, it in enumerate(items[:4]):
        hl = (it.get('headline') or '')[:60]
        print(f"   [{i+1}] {it.get('sentiment')} | {it.get('time')} | pub: {it.get('published_at')} | {hl}...")
    # 3. Check terminal.html
    with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

# Test 2: Backtest Candles
req_c = urllib.request.Request('http://127.0.0.1:8000/api/backtest/candles/RELIANCE?timeframe=5m')
req_c.add_header('Cookie', f'session={cookie_val}')
with urllib.request.urlopen(req_c, timeout=10) as r:
    cd = json.loads(r.read().decode('utf-8'))
    candles = cd.get('candles', [])
    print(f'2. Backtest Candles Test: {len(candles)} candles returned')
    assert 'id="panel-reco"' in html, "panel-reco missing"
    assert 'id="panel-dashboard"' in html, "panel-dashboard missing"
    assert 'chartAiSuggestBtnMobile' in html, "chartAiSuggestBtnMobile missing"
    assert 'calcPureBsGreeks' in html, "calcPureBsGreeks missing"
    assert 'LOCAL FALLBACK' not in html, "LOCAL FALLBACK still present in html"
    print("terminal.html verification passed cleanly!")

# Test 3: Backtest Evaluate
if candles:
    eval_payload = json.dumps({
        'instrument': 'RELIANCE',
        'timeframe': '5m',
        'candles': candles[-50:]
    }).encode('utf-8')
    req_e = urllib.request.Request('http://127.0.0.1:8000/api/backtest/evaluate', data=eval_payload, headers={'Content-Type': 'application/json', 'Cookie': f'session={cookie_val}'}, method='POST')
    with urllib.request.urlopen(req_e, timeout=10) as r:
        res = json.loads(r.read().decode('utf-8'))
        print(f"3. Backtest Evaluate Test: {res.get('recommendation')} | Entry: {res.get('entry')} | SL: {res.get('stop_loss')} | Tgt: {res.get('target')} | EMA20: {res.get('ema_20')} | ATR: {res.get('atr')}")
        print(f"   Rationale: {res.get('rationale')}")

# Test 4: Verify Terminal HTML DOM
req_term = urllib.request.Request('http://127.0.0.1:8000/terminal')
req_term.add_header('Cookie', f'session={cookie_val}')
with urllib.request.urlopen(req_term, timeout=10) as r:
    html = r.read().decode('utf-8')
    print(f'4. Terminal HTML Verification: {len(html)} bytes')
    print('   - panel-dashboard in HTML:', 'id="panel-dashboard"' in html)
    print('   - panel-ca_ai_dashboard in HTML:', 'id="panel-ca_ai_dashboard"' in html)
    print('   - data-tab="dashboard" in HTML:', 'data-tab="dashboard"' in html)
    print('   - panel-backtest in HTML:', 'id="panel-backtest"' in html)
    print('   - chartRecoBanner in HTML:', 'id="chartRecoBanner"' in html)
    print('   - btTaGrid in HTML:', 'id="btTaGrid"' in html)
    print('   - btBullishNewsList in HTML:', 'id="btBullishNewsList"' in html)
    print('   - btBearishNewsList in HTML:', 'id="btBearishNewsList"' in html)
    print('   - btToggleEma in HTML:', 'id="btToggleEma"' in html)
    print('   - btToggleOsc in HTML:', 'id="btToggleOsc"' in html)
    print('   - chartAiPanel mobile styles in HTML:', '#chartAiPanel.ca-chart-ai-panel' in html)
    print('   - computeBacktestIndicators in HTML:', 'computeBacktestIndicators' in html)
    print('   - updateChartRecoBanner in HTML:', 'updateChartRecoBanner' in html)
if __name__ == '__main__':
    verify_all()
