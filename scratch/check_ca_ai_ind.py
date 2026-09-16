import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'CA AI Indicator', html, re.IGNORECASE):
    idx = m.start()
    print("Match at", idx, ":")
    print(html[max(0, idx-100):min(len(html), idx+200)])
    print("="*60)

