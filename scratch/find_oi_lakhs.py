import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
matches = list(re.finditer(r'OI\s*\(LAKHS\)', text, re.I))
print(f"Found {len(matches)} matches for OI (LAKHS)")
for m in matches:
    pos = m.start()
    print("--- Match at", pos, "---")
    print(text[max(0, pos-300):pos+300])
