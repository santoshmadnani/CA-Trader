with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
matches = list(re.finditer(r'CRUDEOIL', c, re.I))
print(f"Found {len(matches)} occurrences of CRUDEOIL in app.py")
for m in matches[:15]:
    idx = m.start()
    print(f"Match at {idx}:")
    print(c[max(0, idx-100):min(len(c), idx+300)])
    print("-" * 50)

