import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

matches = [m.start() for m in re.finditer(r'updateFloatingPositionsWidget', text)]
for idx in matches:
    print(f'=== idx {idx} ===')
    print(text[max(0, idx-40):idx+120])

print('\n=== loadPositions calls ===')
for m in re.finditer(r'loadPositions\b', text):
    idx = m.start()
    print(f'=== loadPositions at {idx} ===')
    print(text[max(0, idx-40):idx+120])

