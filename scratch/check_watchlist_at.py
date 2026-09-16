with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'>AT<|class=["\'][^"\']*wl-at[^"\']*["\']|title=["\'][^"\']*Auto-Trade[^"\']*["\']|btnWlAt', text)]
print("Watchlist AT matches:", len(matches))
for idx in matches:
    print(f"At {idx}:", text[idx-40:idx+200].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

