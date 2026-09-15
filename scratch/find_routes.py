import re

content = open('app.py', encoding='utf-8', errors='ignore').read()
for m in re.finditer(r'@app\.(get|post)\(["\']([^"\']+)["\']', content):
    if any(k in m.group(2) for k in ['reco', 'analysis', 'quote', 'candle']):
        print(m.group(1).upper(), m.group(2))

