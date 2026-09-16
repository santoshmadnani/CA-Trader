with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_reco = text.find('id="panel-reco"')
print(text[idx_reco:idx_reco+1500].encode('ascii', errors='replace').decode('ascii'))

# find next panel after panel-reco
import re
m = re.search(r'<div[^>]+class=["\']panel[^"\']*["\'][^>]+id=["\']panel-([a-zA-Z0-9_-]+)["\']', text[idx_reco+100:])
if m:
    print("Next panel after panel-reco:", m.group(0)[:200])

