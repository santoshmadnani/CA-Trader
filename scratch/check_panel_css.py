with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

for m in re.finditer(r'\.panel(?:\.active|\s*\{|\s*\[)[^}]+\}', text):
    print(m.group(0))
