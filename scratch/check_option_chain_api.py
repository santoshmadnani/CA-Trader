with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'def\s+[a-zA-Z0-9_]*option[a-zA-Z0-9_]*chain\s*\(', text, re.I)
if not m:
    m = re.search(r'/api/market/options/chain/\{[^}]+\}', text)
if m:
    idx = m.start()
    print("Found option chain in app.py:\n", text[idx-100:idx+2500].encode('ascii', errors='replace').decode('ascii'))
else:
    print("Not found by regex")

