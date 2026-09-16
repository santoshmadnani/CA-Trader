with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'/api/positions/\{[^}]+\}/analysis', text)
if m:
    idx = m.start()
    print(text[idx-100:idx+2500].encode('ascii', errors='replace').decode('ascii'))

