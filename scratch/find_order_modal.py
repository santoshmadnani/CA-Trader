with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if any(k in line.lower() for k in ['orderqty', 'orderlot', 'lot size', 'openorder(']):
        print(f"Line {idx+1}: {line.strip()[:100]}")

