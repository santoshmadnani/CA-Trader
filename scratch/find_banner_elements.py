import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'chartRecoEntry', text):
    line_num = text[:m.start()].count('\n') + 1
    line = text[text.rfind('\n', 0, m.start())+1 : text.find('\n', m.start())]
    print(f"Line {line_num}: {line.strip()[:120]}")

print("\nLet's search for chartRecoQuickOrderBtn:")
for m in re.finditer(r'chartRecoQuickOrderBtn', text):
    line_num = text[:m.start()].count('\n') + 1
    line = text[text.rfind('\n', 0, m.start())+1 : text.find('\n', m.start())]
    print(f"Line {line_num}: {line.strip()[:120]}")

