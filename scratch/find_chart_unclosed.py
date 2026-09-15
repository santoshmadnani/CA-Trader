from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
p_start = text.find('<div class="panel" id="panel-charts">')
p_end = text.find('<div class="panel" id="panel-console">')
chunk = text[p_start:p_end]
lines = chunk.splitlines()

depth = 0
for i, line in enumerate(lines):
    opens = len(re.findall(r'<div\b', line))
    closes = len(re.findall(r'</div', line))
    diff = opens - closes
    depth += diff
    if diff != 0:
        print(f"L{i+1:3d} [diff={diff:+2d}, depth={depth:2d}]: {line[:80]}")

