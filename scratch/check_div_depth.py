with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

depth = 0
for idx in range(1956, 2452):
    line = lines[idx]
    opens = line.count('<div')
    closes = line.count('</div')
    depth += opens - closes
    if opens != closes or 'panel' in line:
        print(f"L{idx+1:4d} (+{opens} -{closes} => depth={depth}): {line.strip()[:80]}")

