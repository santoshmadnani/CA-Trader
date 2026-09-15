import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = 0
while True:
    idx = text.find('autoAddSymbolBtn', pos)
    if idx == -1: break
    print(f"Match at {idx}:")
    print(text[max(0, idx-50):min(len(text), idx+600)])
    pos = idx + len('autoAddSymbolBtn') + 20

