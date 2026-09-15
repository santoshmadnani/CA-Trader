from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
for m in re.finditer(r'id=["\']([^"\']*[Rr]eco[^"\']*)["\']', text):
    line = text[:m.start()].count('\n') + 1
    print(f"L{line}: {m.group(1)}")

