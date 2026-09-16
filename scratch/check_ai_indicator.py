import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'id=["\'](?:chartAiPanel|chartAiSuggestBtn|chartAi)[^"\']*["\']', html):
    idx = m.start()
    print("Match at", idx, ":")
    print(html[max(0, idx-100):min(len(html), idx+300)])
    print("="*60)

# Search for any mobile CSS regarding chartAiPanel
for m in re.finditer(r'@media[^{]*\{[^}]*chartAiPanel', html):
    print("Media query match:")
    print(m.group(0))
    print("="*60)

