import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'data-tab', html):
    idx = m.start()
    # Check if this is inside a script tag or listener
    context = html[max(0, idx-100):min(len(html), idx+300)]
    if 'addEventListener' in context or 'click' in context or 'tab' in context:
        print(context)
        print("="*60)

