import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'.{0,60}theta.{0,60}', text, re.IGNORECASE):
    print(m.group(0).strip())

