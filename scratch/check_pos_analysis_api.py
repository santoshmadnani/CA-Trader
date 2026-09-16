with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'def\s+[a-zA-Z0-9_]*pos[a-zA-Z0-9_]*analysis\s*\(', text, re.I)
if not m:
    m = re.search(r'/api/positions/\{[^}]+\}/analysis', text)
if m:
    idx = m.start()
    print("Found endpoint in app.py:\n", text[idx-100:idx+2500])
else:
    print("Not found by regex")

