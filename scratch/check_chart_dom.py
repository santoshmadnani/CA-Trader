with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'id=["\']chartFullscreen["\']', text)
if m:
    idx = m.start()
    print("Around chartFullscreen HTML:\n", text[idx-300:idx+600].encode('ascii', errors='replace').decode('ascii'))

# find the toolbar buttons in chart
m2 = re.search(r'class=["\']chart-toolbar["\']', text)
if m2:
    idx2 = m2.start()
    print("chart-toolbar HTML:\n", text[idx2:idx2+1200].encode('ascii', errors='replace').decode('ascii'))

