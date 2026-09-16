with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'def\s+init_db\s*\(', text)
if m:
    idx = m.start()
    print("init_db in app.py:\n", text[idx:idx+1500].encode('ascii', errors='replace').decode('ascii'))

