import sys; sys.stdout.reconfigure(encoding='utf-8')
import re
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Show last 20 lines with non-zero diffs in panel-dashboard
pd_start = text.find('<div class="panel active" id="panel-dashboard">')
pd_end = text.find('<div class="panel" id="panel-charts">')
chunk = text[pd_start:pd_end]

lines = chunk.splitlines()
depth = 0
results = []
for i, line in enumerate(lines):
    opens = len(re.findall(r'<div\b', line))
    closes = len(re.findall(r'</div', line))
    depth += opens - closes
    if opens != closes:
        results.append(f'L{i+1:3d} d={depth:+3d} ({opens-closes:+2d}): {line[:90]}')

# Show last 30 entries
for r in results[-30:]:
    print(r)
print(f'\nFinal depth: {depth}')
total_lines = len(lines)
print(f'Total lines in panel-dashboard chunk: {total_lines}')
print('Last 5 lines:')
for l in lines[-5:]:
    print(repr(l))

