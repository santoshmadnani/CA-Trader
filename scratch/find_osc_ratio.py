content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'oscHeightRatio', content):
    p = m.start()
    print('Found at', p)
    print(content[p-30:p+200].encode('ascii', errors='replace').decode())

