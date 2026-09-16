import sys; sys.stdout.reconfigure(encoding='utf-8')
import re
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Precisely count all divs in panel-dashboard chunk
pd_start = text.find('<div class="panel active" id="panel-dashboard">')
pd_end = text.find('<div class="panel" id="panel-charts">')
chunk = text[pd_start:pd_end]

# Find the excess unclosed div
lines = chunk.splitlines()
depth = 0
for i, line in enumerate(lines):
    opens = len(re.findall(r'<div\b', line))
    closes = len(re.findall(r'</div', line))
    prev_depth = depth
    depth += opens - closes
    if opens != closes:
        print(f'L{i+1:3d} d={depth:+3d} ({opens-closes:+2d}): {line[:90]}')
print(f'\nFinal depth: {depth}')

