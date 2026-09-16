import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'.{0,80}interactionMode.{0,80}', text):
    print(m.group(0))

