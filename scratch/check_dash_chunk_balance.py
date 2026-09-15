import re
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos_dash = text.find('id="panel-dashboard"')
pos_charts = text.find('id="panel-charts"')

chunk = text[pos_dash:pos_charts]
opens = len(re.findall(r'<div\b[^>]*>', chunk, re.I))
closes = len(re.findall(r'</div>', chunk, re.I))
print(f'Dashboard chunk: opens={opens}, closes={closes}, diff={opens-closes}')
