import subprocess, json

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

test_script = """
import urllib.request, urllib.parse, json, http.cookiejar

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# 1. Login with demo/test credentials or get session
# Let's inspect users or login
login_data = urllib.parse.urlencode({'username': 'santosh', 'password': 'password123'}).encode()
try:
    req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=login_data, method='POST')
    with opener.open(req) as resp:
        print('LOGIN STATUS:', resp.status)
except Exception as e:
    print('LOGIN NOTE:', e)

# 2. Test Crude news feed
try:
    req = urllib.request.Request('http://127.0.0.1:8000/api/news/ca-ai-feed?symbol=CRUDEOIL')
    with opener.open(req) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        print('CRUDE NEWS COUNT:', len(d.get('items', [])))
        for item in d.get('items', [])[:3]:
            print(' - Headline:', item.get('title'))
except Exception as e:
    print('NEWS ERROR:', e)

# 3. Test candlestick pattern detection in app.py
from app import detect_candlestick_patterns
import pandas as pd, numpy as np

# Create sample candles
mock_df = pd.DataFrame({
    'open': [6000, 5950, 5900, 5850, 5800, 5750, 5740, 5700, 5720, 5750],
    'high': [6010, 5960, 5910, 5860, 5810, 5760, 5750, 5730, 5760, 5820],
    'low':  [5940, 5890, 5840, 5790, 5740, 5720, 5710, 5690, 5710, 5740],
    'close':[5950, 5900, 5850, 5800, 5750, 5730, 5720, 5725, 5750, 5810],
    'volume':[1000]*10,
    'timestamp': ['2026-09-16 10:00', '2026-09-16 10:05', '2026-09-16 10:10', '2026-09-16 10:15', '2026-09-16 10:20', '2026-09-16 10:25', '2026-09-16 10:30', '2026-09-16 10:35', '2026-09-16 10:40', '2026-09-16 10:45']
})
patterns = detect_candlestick_patterns(mock_df)
print('DETECTED PATTERNS COUNT:', len(patterns))
for p in patterns[:4]:
    print(' Pattern:', p.get('name'), '| Type:', p.get('type'), '| Candle Time:', p.get('candle_time'), '| Detected At:', p.get('detected_at'))
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
       f'sudo docker exec ca-trader python3 -c "{test_script}"']
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)
if r.stderr:
    print("STDERR:\n", r.stderr)

