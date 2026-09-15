import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 0
while True:
    pos = text.find('caEditBar', idx)
    if pos == -1: break
    print(f"Match at {pos}:")
    print(text[max(0, pos-40):min(len(text), pos+150)])
    idx = pos + 10

