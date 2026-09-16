import sys; sys.stdout.reconfigure(encoding='utf-8')
import re
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# The panel-dashboard chunk includes the OPENING tag of panel-dashboard 
# AND ends just before panel-charts opening tag.
# The depth starts at 0, when we hit <div class="panel active" id="panel-dashboard"> it goes to +1
# The final depth 1 means the panel-dashboard opening div is never closed within the chunk
# That is correct because panel-dashboard ends with </div> which closes the panel ITSELF
# Let's check: the chunk should end at depth=0 (opening div was opened and closed)
# But it shows depth=1 - which means there's ONE extra unclosed open div inside

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
        results.append((i+1, depth, opens-closes, line[:90]))

print(f'Final depth (should be 0): {depth}')
print(f'Total lines: {len(lines)}')
print(f'Lines with diff != 0:')
for r in results[-10:]:
    print(f'  L{r[0]:3d} d={r[1]:+3d} ({r[2]:+2d}): {r[3]}')

# The trace_all_panels.py script must be counting differently
# Let's see what it's counting:
# It says open=95, close=94. This is 95 divs opened, 94 closed
# diff=1 means one more open than close. 
# Since the panel-dashboard div itself opens and closes, the net should be 0.
# depth=1 at the end with open=95 close=94 both make sense -- the final </div> that closes
# panel-dashboard is likely included in the chunk since it comes before panel-charts.
# Let's check:
print('\nLast 10 lines of chunk:')
for l in lines[-10:]:
    print(repr(l))

