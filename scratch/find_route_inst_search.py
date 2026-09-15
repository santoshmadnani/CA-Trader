with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
m = re.search(r'@app\.get\(["\']/api/instruments/search["\']\)', c)
if m:
    idx = m.start()
    print(f"@app.get('/api/instruments/search') at {idx}:")
    print(c[idx:idx+2500])
else:
    print("Not found with exact decorator")

