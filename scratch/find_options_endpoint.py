with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
for m in re.finditer(r'/api/options[a-zA-Z0-9_/-]*', c):
    idx = m.start()
    print(f"Match {m.group(0)} at {idx}:")
    print(c[max(0, idx-50):min(len(c), idx+300)])
    print("-" * 50)

