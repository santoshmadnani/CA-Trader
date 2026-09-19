with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'function showTab\s*\([^\)]*\)\s*\{', text)
if m:
    pos = m.start()
    ln = text[:pos].count('\n') + 1
    print(f"showTab defined at line {ln}:")
    print(text[pos:pos+1500])
else:
    print("function showTab not found directly, searching regex...")
    for m in re.finditer(r'showTab\s*=\s*function|showTab\s*\(', text):
        pos = m.start()
        ln = text[:pos].count('\n') + 1
        print(f"showTab match at {ln}: {text[pos:pos+200]}")
