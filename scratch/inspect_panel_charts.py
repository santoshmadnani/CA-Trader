with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
# find start of panel-charts
p_start = text.find('id="panel-charts"')
p_end = text.find('id="panel-', p_start + 20)
print("panel-charts length:", p_end - p_start)
charts_content = text[p_start:p_end]

for m in re.finditer(r'<div[^>]+id=["\']([^"\']+)["\'][^>]*>', charts_content):
    elem_id = m.group(1)
    if any(k in elem_id.lower() for k in ['summary', 'tech', 'pattern', 'factor', 'news', 'reco', 'greek', 'opt']):
        print("Elem in panel-charts:", elem_id)

card_titles = re.findall(r'class=["\'](?:card-title|section-title)[^"\']*["\'][^>]*>([^<]+)<', charts_content)
print("Card/section titles in panel-charts:", card_titles[:15])

