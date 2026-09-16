with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4550, min(4600, len(lines))):
    print(f"{i+1}: {lines[i].encode('ascii', errors='replace').decode('ascii')}", end="")

