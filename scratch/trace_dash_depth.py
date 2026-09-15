import re

with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos_dash = text.find('id="panel-dashboard"')
pos_charts = text.find('id="panel-charts"')
chunk = text[pos_dash:pos_charts]

lines = chunk.splitlines()
depth = 0
for idx, line in enumerate(lines):
    op = len(re.findall(r'<div\b[^>]*>', line, re.I))
    cl = len(re.findall(r'</div>', line, re.I))
    depth += (op - cl)
    if op or cl:
        # print if depth changes
        if idx > len(lines) - 20:
            print(f"Line {idx} (depth={depth}): {line.strip()}")

print("Final depth:", depth)
