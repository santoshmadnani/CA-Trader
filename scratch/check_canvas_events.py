with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# find canvas mouse/touch event listeners
m = re.search(r'addEventListener\(["\'](mousemove|touchstart|touchmove|wheel)["\']', text)
if m:
    print("Found canvas event listener near:", m.start())

# search for "upstoxCandles" event listeners
for m in re.finditer(r'upstoxCandles.*addEventListener', text):
    idx = m.start()
    print("upstoxCandles listener:\n", text[idx:idx+500].encode('ascii', errors='replace').decode('ascii'))
    print("="*40)

# check how crosshair is rendered
m2 = re.search(r'function\s+drawCrosshair\s*\(|//\s*Crosshair', text, re.I)
if m2:
    idx2 = m2.start()
    print("Crosshair code:\n", text[idx2:idx2+800].encode('ascii', errors='replace').decode('ascii'))

