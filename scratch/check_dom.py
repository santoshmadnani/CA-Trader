import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

main = soup.find('div', class_='main')
if not main:
    print("No .main div found!")
else:
    print("Direct children of .main:")
    for child in main.children:
        if child.name:
            c_id = child.get('id', '(no-id)')
            c_cls = child.get('class', [])
            print(f"  <{child.name} id='{c_id}' class='{' '.join(c_cls)}'>")

print("\nAll .panel elements in document and their parents:")
for p in soup.find_all('div', class_='panel'):
    p_id = p.get('id', '(no-id)')
    parent = p.parent
    parent_id = parent.get('id', '(no-id)') if parent else 'None'
    parent_cls = ' '.join(parent.get('class', [])) if parent else ''
    print(f"  Panel #{p_id} -> parent: <{parent.name} id='{parent_id}' class='{parent_cls}'>")

