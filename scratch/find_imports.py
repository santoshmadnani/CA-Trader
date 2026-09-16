import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'^(?:import|from)\s+[^\n]+', text, re.MULTILINE):
    print(m.group(0))
    if m.start() > 10000:
        break

