import sys; sys.stdout.reconfigure(encoding='utf-8')
import re
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

pd_start = text.find('<div class="panel active" id="panel-dashboard">')
pd_end = text.find('<div class="panel" id="panel-charts">')
chunk = text[pd_start:pd_end]
lines = chunk.splitlines()

# Find lines near L241 in the chunk to understand what's happening
print(f'Lines 225-262 of panel-dashboard chunk:')
for i in range(225, min(265, len(lines))):
    opens = len(re.findall(r'<div\b', lines[i]))
    closes = len(re.findall(r'</div', lines[i]))
    diff = opens - closes
    print(f'L{i+1:3d} ({diff:+d}): {lines[i][:100]}')

