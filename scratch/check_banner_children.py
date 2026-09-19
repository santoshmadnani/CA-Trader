from bs4 import BeautifulSoup
import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
banner = soup.find('div', id='chartRecoBanner')
print("Direct children of #chartRecoBanner:")
for c in banner.children:
    if c.name:
        c_id = c.get('id', '(no-id)')
        c_cls = ' '.join(c.get('class', []))
        print(f"  <{c.name} id='{c_id}' class='{c_cls}'>")

print("banner tag:", banner.name, banner.get('id'))
print("banner children count:", len(list(banner.children)))
for ch in banner.children:
    if hasattr(ch, 'name') and ch.name:
        print(f"  <{ch.name} id='{ch.get('id', '')}' class='{ch.get('class', '')}'>")
