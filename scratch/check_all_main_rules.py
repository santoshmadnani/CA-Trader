import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'\.main\s*\{[^}]*\}', text)
while m:
    print(m.group(0))
    text = text[m.end():]
    m = re.search(r'\.main\s*\{[^}]*\}', text)
