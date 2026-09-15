content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'(const|let|var|function)\s+selectedSymbol', content):
    p = m.start()
    print(content[p:p+300])

