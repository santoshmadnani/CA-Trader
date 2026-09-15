import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
for fn in ['renderOptionChain', 'loadOptions', 'fetchOptionChain', 'optChainTable', 'optionChain']:
    matches = list(re.finditer(fn, c))
    print(f"{fn}: {len(matches)} occurrences")
    for m in matches[:2]:
        idx = m.start()
        print(f"  at {idx}: {c[max(0, idx-50):min(len(c), idx+150)]}")

