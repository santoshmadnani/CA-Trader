with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'function\s+updateLiveCandle\s*\([^)]*\)\s*\{', text)
if m:
    idx = m.start()
    print(text[idx:idx+1500].encode('ascii', errors='replace').decode('ascii'))

