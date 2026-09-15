from bs4 import BeautifulSoup
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
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
