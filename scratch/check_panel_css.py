import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
print("Matches for panel-options in styles:")
for m in re.finditer(r'#panel-options[^{]*\{[^}]*\}', text):
    print(m.group(0))

print("\nMatches for .panel in styles:")
for m in re.finditer(r'\.panel[^{]*\{[^}]*\}', text):
    print(m.group(0))

print("\nMatches for .content in styles:")
for m in re.finditer(r'\.content[^{]*\{[^}]*\}', text):
    print(m.group(0))

