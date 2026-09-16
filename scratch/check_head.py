import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'floatingPosHead', text):
    idx = m.start()
    print(f'=== floatingPosHead at {idx} ===')
    print(text[max(0, idx-50):idx+250])

