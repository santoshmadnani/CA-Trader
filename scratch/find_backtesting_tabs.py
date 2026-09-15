with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
matches = list(re.finditer(r'Backtesting', c, re.I))
print(f"Found {len(matches)} occurrences of Backtesting")
for m in matches[:10]:
    idx = m.start()
    print(f"Match at {idx}:")
    print(c[max(0, idx-60):min(len(c), idx+100)])
    print("-" * 50)

