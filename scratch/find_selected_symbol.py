content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'selectedSymbol', content):
    p = m.start()
    print('---')
    print(content[p-50:p+200])

