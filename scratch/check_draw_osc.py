with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'function\s+draw\s*\(\s*\)\s*\{', text)
if m:
    idx = m.start()
    print(text[idx+2500:idx+6000].encode('ascii', errors='replace').decode('ascii'))

