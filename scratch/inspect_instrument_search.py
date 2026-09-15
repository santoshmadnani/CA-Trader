import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('id="instrumentSearch"')
print("--- instrumentSearch HTML ---")
print(c[p-100:p+500])

# Find where instrumentSearch is used in JS
import re
print("\n--- instrumentSearch JS occurrences ---")
for m in re.finditer(r'instrumentSearch', c):
    idx = m.start()
    print(f"Match at {idx}:")
    print(c[max(0, idx-100):min(len(c), idx+300)])
    print("-" * 50)

