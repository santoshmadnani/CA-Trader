import sys

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def analysis_overall' in l:
        print(f"analysis_overall at line {i+1}:")
        for j in range(max(0, i-5), min(len(lines), i+60)):
            print(f"{j+1}: {lines[j]}", end='')
        break

