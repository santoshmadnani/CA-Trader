from bs4 import BeautifulSoup
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(text, 'html.parser')

tab = soup.find(id='dashboardTab')
if tab:
    print("dashboardTab tag:", tab.name, "class:", tab.get('class'), "style:", tab.get('style'))
    parent = tab.parent
    while parent and parent.name != '[document]':
        print("  parent:", parent.name, "id:", parent.get('id'), "class:", parent.get('class'))
        parent = parent.parent
panels = soup.find_all(class_='panel')
for p in panels:
    parent_id = p.parent.get('id') if p.parent else 'None'
    parent_class = p.parent.get('class') if p.parent else 'None'
    print(f"Panel id={p.get('id')}: parent=<{p.parent.name} id={parent_id} class={parent_class}>")
