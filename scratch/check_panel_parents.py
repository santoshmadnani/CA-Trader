import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()
from bs4 import BeautifulSoup

pos = text.find('id="panel-options"')
# find opening divs before this
before = text[:pos]
lines = before.splitlines()
print("\n".join(lines[-25:]))
with open('terminal.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    html = f.read()

panels = soup.find_all('div', class_=lambda c: c and 'panel' in c.split())
soup = BeautifulSoup(html, 'html.parser')

panels = soup.find_all(class_='panel')
print(f"Total panels found: {len(panels)}")
for p in panels:
    pid = p.get('id', 'no-id')
    pid = p.get('id', 'NO_ID')
    parent = p.parent
    p_classes = parent.get('class', [])
    p_id = parent.get('id', '')
    print(f"Panel #{pid:25s} -> Parent: <{parent.name} id='{p_id}' class='{' '.join(p_classes) if p_classes else ''}'>")
    parent_tag = parent.name if parent else 'None'
    parent_id = parent.get('id', 'no-id') if parent else ''
    parent_class = parent.get('class', []) if parent else []
    
    # check parents chain
    chain = []
    curr = p
    while curr and curr.name != '[document]':
        cid = curr.get('id', '')
        ccls = '.'.join(curr.get('class', []))
        chain.append(f"{curr.name}#{cid}.{ccls}")
        curr = curr.parent
    chain.reverse()
    print(f"Panel: {pid:<25} Parent: {parent_tag}#{parent_id} ({parent_class})")
    print(f"  Hierarchy: {' > '.join(chain[-4:])}")
