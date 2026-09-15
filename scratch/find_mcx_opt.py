content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'mcxOptSymbol', content):
    p = m.start()
    print('Found at', p)
    print(content[p-40:p+200].encode('ascii', errors='replace').decode())

