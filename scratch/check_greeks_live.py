with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'calcPureBsGreeks|dashGreeks|dashGamma|dashDelta', text)]
for idx in matches:
    print(f"At {idx}:", text[idx-30:idx+200].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

