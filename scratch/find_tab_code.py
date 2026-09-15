with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'showtab' in line.lower() or 'data-tab' in line.lower() or 'navtab' in line.lower():
        print(f"{i+1}: {line.strip()[:120]}")

