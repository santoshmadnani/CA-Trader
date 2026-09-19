from bs4 import BeautifulSoup
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Let's inspect the positions and parents of all panel- divs
for m in re.finditer(r'<div[^>]*\bid=["\'](panel-[^"\']+)["\'][^>]*>', html):
    pos = m.start()
    id_name = m.group(1)
    tag_str = m.group(0)
    # Check parent context
    before = html[max(0, pos-200):pos]
    print(f"Panel: {id_name}")
    print(f"  Tag: {tag_str}")
    # Find last open div before this
    parent_matches = re.findall(r'<div\b[^>]*\bid=["\']([^"\']+)["\']', before)
    print(f"  Nearest preceding ID: {parent_matches[-1] if parent_matches else 'none'}")
soup = BeautifulSoup(html, 'html.parser')
panels = soup.find_all(class_='panel')
print(f"Total panels found: {len(panels)}")
for p in panels:
    pid = p.get('id', 'NO_ID')
    parent = p.parent
    parent_info = f"{parent.name}#{parent.get('id', '')}.{'.'.join(parent.get('class', []))}"
    print(f"Panel: {pid:<25} -> Parent: {parent_info}")
