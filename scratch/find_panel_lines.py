import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

panels = []
for i, line in enumerate(lines):
    m = re.search(r'id=["\'](panel-[a-z0-9-]+)["\']', line)
    if m:
        panels.append((i+1, m.group(1), line.strip()))

for p in panels:
    print(f"Line {p[0]}: {p[1]} -> {p[2][:80]}")
