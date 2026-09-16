import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'indicators', html):
    idx = m.start()
    context = html[max(0, idx-50):min(len(html), idx+200)]
    if 'innerHTML' in context or 'render' in context or 'tbody' in context or 'table' in context:
        print("Match at", idx, ":")
        print(context)
        print("="*60)

