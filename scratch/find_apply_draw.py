content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'applyDrawingPoint', content):
    p = m.start()
    print('Found at', p)
    print(content[p-50:p+1200].encode('ascii', errors='replace').decode())

