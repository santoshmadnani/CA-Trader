import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'@media[^{]*max-width:\s*(?:768|760|600|480)px[^{]*\{', html):
    idx = m.start()
    print("Media query at", idx, ":")
    print(html[idx:idx+500])
    print("="*60)

