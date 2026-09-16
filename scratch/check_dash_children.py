import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's inspect panel-dashboard tag by tag
soup = BeautifulSoup(html, 'html.parser')
dash = soup.find('div', id='panel-dashboard')

print("Direct children of #panel-dashboard:")
for c in dash.children:
    if c.name:
        c_id = c.get('id', '(no-id)')
        c_cls = ' '.join(c.get('class', []))
        print(f"  <{c.name} id='{c_id}' class='{c_cls}'>")

