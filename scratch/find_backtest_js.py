import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = 0
found = []
while True:
    idx = text.find('backtest', pos)
    if idx == -1: break
    found.append(idx)
    pos = idx + len('backtest') + 5

print(f"Total occurrences of 'backtest': {len(found)}")
for p in found[:10]:
    print(f"At {p}: {text[p-20:p+60]}")

