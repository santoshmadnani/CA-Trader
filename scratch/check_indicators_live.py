with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# search for "waiting for value"
matches = [m.start() for m in re.finditer(r'waiting for value', text, re.I)]
print("Total occurrences of 'waiting for value':", len(matches))
for idx in matches:
    print(f"At {idx}:")
    print(text[idx-60:idx+250].encode('ascii', errors='replace').decode('ascii'))
    print("="*40)

# search for updateLiveCandle
m2 = re.search(r'function\s+updateLiveCandle\s*\(', text)
if m2:
    idx2 = m2.start()
    print("updateLiveCandle function:\n", text[idx2:idx2+1200].encode('ascii', errors='replace').decode('ascii'))

