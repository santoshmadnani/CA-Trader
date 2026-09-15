import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
print("Looking for indicator cards/lists in HTML:")
for m in re.finditer(r'id=[\"\']([a-zA-Z0-9_-]*ind[a-zA-Z0-9_-]*|technical[a-zA-Z0-9_-]*)[\"\']', c, re.I):
    print(" ", m.group(0), "at", m.start())

