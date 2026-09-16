import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Search for mobile nav / mobile bar
for m in re.finditer(r'mobile-(?:nav|bar|footer|dock|header)', html):
    idx = m.start()
    print("Match at", idx, ":")
    print(html[max(0, idx-50):min(len(html), idx+200)])
    print("="*60)

