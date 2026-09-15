content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'function selectInstrument\(', content):
    p = m.start()
    print(content[p:p+1200])

