with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m2 = re.search(r'<div[^>]*class=["\'][^"\']*chart-toolbar[^"\']*["\']', text)
if m2:
    idx2 = m2.start()
    print("chart-toolbar HTML:\n", text[idx2:idx2+1200].encode('ascii', errors='replace').decode('ascii'))
else:
    print("chart-toolbar not found by exact class, searching for toolbars in panel-charts:")
    m3 = re.search(r'id=["\']panel-charts["\']', text)
    if m3:
        idx3 = m3.start()
        print(text[idx3:idx3+1500].encode('ascii', errors='replace').decode('ascii'))

