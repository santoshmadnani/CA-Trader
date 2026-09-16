from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

text = Path('app.py').read_text(encoding='utf-8')
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

print("Overall & Recommendation endpoints in app.py:")
for m in re.finditer(r'@app\.(?:get|post)\(["\']([^"\']+)["\']', text):
    path = m.group(1)
    if any(k in path.lower() for k in ['factor', 'macro', 'market', 'ai', 'global', 'other']):
        line = text[:m.start()].count('\n') + 1
        print(f"L{line}: {path}")

    ep = m.group(1)
    if 'recom' in ep or 'overall' in ep or 'analysis' in ep:
        print(" ", ep)
