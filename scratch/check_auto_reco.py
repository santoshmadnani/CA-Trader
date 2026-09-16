with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'dashAutoRecoStrip|auto_trade|next_recommendation|every 5 minute', text, re.I)]
print("Auto reco matches in terminal.html:", len(matches))
for idx in matches[:10]:
    print(f"At {idx}:", text[idx-30:idx+200].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

