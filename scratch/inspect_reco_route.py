import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'@app\.get\(["\'][^"\']*recom[^"\']*["\']\)', text):
    print(m.group(0))

