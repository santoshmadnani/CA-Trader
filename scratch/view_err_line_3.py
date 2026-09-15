import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(8895, min(len(lines), 8915)):
    print(f"{i+1}: {lines[i]}", end='')

