with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
matches = [m.start() for m in re.finditer(r'showTab', text)]
print(f"Total showTab occurrences: {len(matches)}")
lines = text.splitlines()
for i, line in enumerate(lines):
    if 'showtab' in line.lower():
        print(f"{i+1}: {line.strip()[:80].encode('ascii', 'replace').decode()}")

    if 'showTab' in line and ('function' in line or 'window.showTab' in line or 'const showTab' in line or 'let showTab' in line or 'var showTab' in line):
        print(f"L{i+1}: {line.strip()[:100]}")
