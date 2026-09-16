with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# find event listeners on chartViewport or canvas
m = re.findall(r'(?:chartViewport|c\.addEventListener|v\.addEventListener).*', text[265000:310000])
print("Listeners/events found in chart region:")
for line in m[:30]:
    print(" ->", line[:100])

# search for "crosshair" in this region
for m in re.finditer(r'crosshair', text[265000:310000], re.I):
    idx = 265000 + m.start()
    print("Crosshair in chart engine:\n", text[idx-50:idx+400].encode('ascii', errors='replace').decode('ascii'))
    print("="*40)

