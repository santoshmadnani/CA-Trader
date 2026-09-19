import re
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

content = open('app.py', encoding='utf-8', errors='ignore').read()
for m in re.finditer(r'@app\.(get|post)\(["\']([^"\']+)["\']', content):
    if any(k in m.group(2) for k in ['reco', 'analysis', 'quote', 'candle']):
        print(m.group(1).upper(), m.group(2))
with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()
    text = f.read()

def find_routes():
    pattern = r'(@app\.(?:get|post)\(["\']/api/recommendations[^\n]*)'
    for m in re.finditer(pattern, app):
        idx = m.start()
        print(app[idx:idx+1500])
        print("="*60)

find_routes()
routes = re.findall(r'@app\.(?:get|post|put|delete|patch)\([\'\"]([^\'\"]+)[\'\"]', text)
for r in routes:
    if any(k in r.lower() for k in ['ai', 'analy', 'diag', 'reco', 'chat', 'copilot', 'advisor', 'bot', 'gemini', 'overall']):
        print(r)
