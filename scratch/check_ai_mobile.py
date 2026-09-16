import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'chartAiSuggestBtn', html):
    idx = m.start()
    print("Match around:", html[max(0, idx-100):min(len(html), idx+200)])
    print("="*60)

# Check all references in @media
for m in re.finditer(r'@media[^{]*\{[^\}]*chartAi', html):
    print("Media query match:")
    print(m.group(0))
    print("="*60)

