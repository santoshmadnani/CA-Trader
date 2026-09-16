with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'data-wl-at', text)
if m:
    print("Found data-wl-at at:", m.start())
    print(text[m.start()-100:m.start()+200].encode('ascii', errors='replace').decode('ascii'))
else:
    print("data-wl-at not found")

m2 = re.search(r'function\s+renderWatchlist\s*\(', text)
if m2:
    print("renderWatchlist found at:", m2.start())
    print(text[m2.start():m2.start()+1500].encode('ascii', errors='replace').decode('ascii'))

