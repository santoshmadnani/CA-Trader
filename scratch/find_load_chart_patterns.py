import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
matches = list(re.finditer(r'loadChartPatterns', c))
print(f"Found {len(matches)} occurrences of loadChartPatterns in terminal.html")
for m in matches:
    idx = m.start()
    print(f"Match at {idx}:")
    print(c[max(0, idx-80):min(len(c), idx+150)])
    print("-" * 50)

