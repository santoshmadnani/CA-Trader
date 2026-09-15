import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
print("Matches for .app-body or .layout:")
for m in re.finditer(r'(?:\.app-body|\.layout|\.sidebar)[^{]*\{[^}]*\}', text):
    print(m.group(0))

