import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
pos = text.find('id="optionChainTable"')
print("optionChainTable HTML:")
print(text[pos-200:pos+500])

print("\nStyles for optionChainTable or options-dynamic or table-wrap:")
for m in re.finditer(r'(?:#optionChainTable|\.options-dynamic|\.opt-table|\.table-wrap)[^{]*\{[^}]*\}', text):
    print(m.group(0))

