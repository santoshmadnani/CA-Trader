import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

banner = soup.find('div', id='chartRecoBanner')
print("Direct children of #chartRecoBanner:")
for c in banner.children:
    if c.name:
        c_id = c.get('id', '(no-id)')
        c_cls = ' '.join(c.get('class', []))
        print(f"  <{c.name} id='{c_id}' class='{c_cls}'>")

