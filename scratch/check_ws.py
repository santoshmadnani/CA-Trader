import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'onmessage\b|WebSocket\b', text):
    idx = m.start()
    print(f'=== WS at {idx} ===')
    print(text[max(0, idx-30):idx+150])

