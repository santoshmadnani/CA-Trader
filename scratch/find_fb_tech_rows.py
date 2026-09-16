with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'fallbackTechnicalRows' in l:
        print(f"Line {i+1}: {l.strip()[:120]}")

