with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print('Length:', len(text))
print('Lines:', text.count('\n'))

import re
print("Length of terminal.html:", len(text))
matches = re.findall(r'id=["\']([a-zA-Z0-9_-]*(?:tab|section|panel)[a-zA-Z0-9_-]*)["\']', text, re.I)
print("Tab/panel ids found:", sorted(list(set(matches))))
print('Panels found:')
for m in re.finditer(r'id=["\']panel-[^"\']+["\']', text):
    print(' ', m.group(0))

nav_matches = re.findall(r'<nav[^>]*>.*?</nav>', text, re.DOTALL | re.I)
print("Nav elements:", len(nav_matches))
for n in nav_matches:
    print("NAV:", n[:300])

# Let's search for function that switches tabs or sections
funcs = re.findall(r'function\s+([a-zA-Z0-9_]*(?:Tab|Section|Panel|Nav)[a-zA-Z0-9_]*)\s*\(', text, re.I)
print("Functions related to tab/section:", set(funcs))

print('Navigation buttons/tabs found:')
for m in re.finditer(r'<button[^>]*class=["\'][^"\']*(?:nav|tab)[^"\']*["\'][^>]*>.*?</button>', text, re.DOTALL):
    s = m.group(0).replace('\n', ' ')
    if len(s) > 120:
        s = s[:120] + '...'
    print(' ', s)
