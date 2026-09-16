with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# find navtabs HTML
m = re.search(r'id=["\']navtabs["\'][^>]*>(.*?)</(?:div|ul|nav)', text, re.DOTALL | re.I)
if m:
    print("navtabs HTML snippet:", m.group(0)[:600])

# find showTab definition
m2 = re.search(r'function\s+showTab\s*\([^)]*\)\s*\{', text)
if m2:
    start = m2.start()
    print("showTab function snippet:\n", text[start:start+1200])

# find event listeners on navtabs or tab buttons
m3 = re.findall(r'navtabs.*', text)
print("navtabs references count:", len(m3))
for x in m3[:5]:
    print(" ->", x[:120])
