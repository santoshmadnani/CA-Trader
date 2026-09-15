import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
matches = list(re.finditer(r'function renderChartRecoData', c))
print(f"Found {len(matches)} occurrences of renderChartRecoData")
for m in matches:
    idx = m.start()
    print(f"Match at {idx}:")
    print(c[idx:idx+2500])
    print("=" * 50)

