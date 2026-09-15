import re

with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

for m in re.finditer(r'id=["\']watchlist["\']', text):
    p = m.start()
    print('id=watchlist found at', p)
    print(text[p-50:p+300].encode('ascii', errors='replace').decode())

# Search for where watchlist HTML element is used in JS
for m in re.finditer(r"getElementById\(['\"]watchlist['\"]\)|querySelector\(['\"]#watchlist['\"]\)", text):
    p = m.start()
    print('watchlist element used at', p)
    print(text[p-50:p+400].encode('ascii', errors='replace').decode())

