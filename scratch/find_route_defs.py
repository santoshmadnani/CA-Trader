import sys
import os
sys.path.insert(0, os.path.abspath('.'))

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '/api/backtest' in line or '/api/recommendations/history' in line or '/api/analysis/overall' in line:
        print(f"Line {i+1}: {line.strip()}")
        if i+1 < len(lines):
            print(f"  Next line: {lines[i+1].strip()}")

