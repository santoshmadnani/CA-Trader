from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
modals = re.findall(r'id=["\']([^"\']*[Mm]odal[^"\']*)["\']', text)
print("Modals found:", modals)
for m in set(modals):
    pos = text.find(f'id="{m}"')
    if pos != -1:
        line = text[:pos].count('\n') + 1
        print(f"{m} at line {line}")

