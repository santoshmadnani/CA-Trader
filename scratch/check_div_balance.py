import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

pos_dash = text.find('id="panel-dashboard"')
pos_reco = text.find('id="panel-reco"')

dash_snippet = text[pos_dash:pos_reco]
import re
panels = list(re.finditer(r'<div[^>]*id=["\'](panel-[^"\']+)["\'][^>]*>', text))

for i in range(len(panels)):
    start = panels[i].start()
    panel_id = panels[i].group(1)
    end = panels[i+1].start() if i + 1 < len(panels) else text.find('</main>', start)
    if end == -1:
        end = text.find('</div>\n</div>\n<script', start)
    chunk = text[start:end]
    # count div tags
    opens = len(re.findall(r'<div\b[^>]*>', chunk, re.I))
    closes = len(re.findall(r'</div>', chunk, re.I))
    print(f"{panel_id}: opens={opens}, closes={closes}, diff={opens-closes}")

opens = len(re.findall(r'<div[\s>]', dash_snippet))
closes = len(re.findall(r'</div>', dash_snippet))
print(f"Inside panel-dashboard up to panel-reco: opens = {opens}, closes = {closes}, diff = {opens - closes}")
