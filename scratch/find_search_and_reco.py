with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

import re
print("--- Watchlist search elements ---")
for m in re.finditer(r'id=["\']([a-zA-Z0-9_-]*search[a-zA-Z0-9_-]*)["\']', c, re.I):
    print(" ", m.group(0), "at", m.start())

print("\n--- Reco elements ---")
for m in re.finditer(r'id=["\']([a-zA-Z0-9_-]*reco[a-zA-Z0-9_-]*)["\']', c, re.I):
    print(" ", m.group(0), "at", m.start())

print("\n--- Evaluating text ---")
for m in re.finditer(r'EVALUATING', c, re.I):
    print("  EVALUATING at", m.start())
    print(c[m.start()-50:m.start()+350])

