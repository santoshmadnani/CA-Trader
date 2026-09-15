with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'showtab' in line.lower():
        print(f"{i+1}: {line.strip()[:80].encode('ascii', 'replace').decode()}")

