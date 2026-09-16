import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Searching for navigation/tab switches:")
for m in re.finditer(r'<[^>]+(?:panel-reports|reports)[^>]*>', text):
    print("Tag:", m.group(0))

print("\nSearching for nav container / section bar:")
matches = re.findall(r'<nav[^>]*>.*?</nav>', text, re.DOTALL)
for m in matches:
    print("NAV (first 300 chars):", m[:300])

print("\nSearching for tab click or switchPanel / switchTab functions:")
for m in re.finditer(r'function\s+(?:switchTab|showPanel|setTab|selectTab|openPanel|navTo)[^{]+', text):
    print("Func:", m.group(0))

for m in re.finditer(r'data-(?:tab|panel)=["\'][^"\']+["\']', text):
    print("Attr:", m.group(0))

