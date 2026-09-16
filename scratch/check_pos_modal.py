with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'posAnalysisModal', text)]
for idx in matches:
    print(f"Match at {idx}:")
    print(text[idx-100:idx+600])
    print("="*40)

