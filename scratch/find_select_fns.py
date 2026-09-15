content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'function (select|load|switch|change)[A-Za-z0-9_]*\(', content):
    print(m.group(0))

