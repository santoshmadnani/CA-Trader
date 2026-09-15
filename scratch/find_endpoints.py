from pathlib import Path
import re

text = Path('app.py').read_text(encoding='utf-8')
for m in re.finditer(r'@app\.(?:get|post)\(["\']([^"\']+)["\']', text):
    path = m.group(1)
    if any(k in path.lower() for k in ['factor', 'macro', 'market', 'ai', 'global', 'other']):
        line = text[:m.start()].count('\n') + 1
        print(f"L{line}: {path}")

