with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'state\.appliedIndicators', text)]
print("state.appliedIndicators occurrences:", len(matches))
for idx in matches[:10]:
    print(f"At {idx}:")
    print(text[idx-40:idx+250].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

