import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'\.chart-toolbar[^{]*\{[^}]*\}', html):
    print("Match:")
    print(m.group(0))
    print("="*60)

