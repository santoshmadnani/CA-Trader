import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'dashRationale|recommendationRationale|recoRationale|historicalRationale', html):
    idx = m.start()
    print("Match at", idx, ":")
    print(html[max(0, idx-100):min(len(html), idx+400)])
    print("="*60)

