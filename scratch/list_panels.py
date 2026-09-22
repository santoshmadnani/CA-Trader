import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'<div[^>]*id=["\'](panel-[^"\']+)["\'][^>]*>', text):
    print(m.group(0))

with open("terminal.html", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if 'id="panel-' in line:
            print(f"{i+1}: {line.strip()[:60]}")
