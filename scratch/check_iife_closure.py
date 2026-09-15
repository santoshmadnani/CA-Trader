import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(7700, 8099):
    line = lines[i]
    if line.strip().startswith('})();') or line.strip().startswith('})()') or line.strip() == '})();':
        print(f"Line {i+1}: {line.strip()}")

