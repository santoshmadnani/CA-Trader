with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'CREATE TABLE IF NOT EXISTS', text)]
print("Total CREATE TABLE occurrences:", len(matches))
for idx in matches[:5]:
    print(f"At {idx}:", text[idx:idx+250].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

