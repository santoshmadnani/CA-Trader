with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'option_chain\(', text)]
for idx in matches:
    print(f"At {idx}:", text[idx-50:idx+250].encode('ascii', errors='replace').decode('ascii'))

