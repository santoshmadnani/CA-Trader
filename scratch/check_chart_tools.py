with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# find chart header/toolbar HTML
m = re.search(r'id=["\']chartHeaderActions["\']', text)
if not m:
    m = re.search(r'class=["\']chart-head["\']|class=["\']chart-toolbar["\']', text)
if m:
    idx = m.start()
    print("Chart header snippet:\n", text[idx-50:idx+1200].encode('ascii', errors='replace').decode('ascii'))

# search for fullscreen button
for m in re.finditer(r'(?:fullscreen|full-screen|btnChartFull|toggleFullscreen)[a-zA-Z0-9_-]*', text, re.I):
    idx = m.start()
    print("Fullscreen match:", text[idx-30:idx+60].encode('ascii', errors='replace').decode('ascii'))

# search for crosshair
for m in re.finditer(r'crosshair', text, re.I):
    idx = m.start()
    print("Crosshair match:", text[idx-30:idx+80].encode('ascii', errors='replace').decode('ascii'))
    break

