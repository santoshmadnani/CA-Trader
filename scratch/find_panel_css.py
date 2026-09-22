from pathlib import Path
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

text = Path('terminal.html').read_text(encoding='utf-8')
# find in style all occurrences of panel-charts, chart, main, etc.
style_end = text.find('</style>')
styles = text[:style_end]
style_content = text[:style_end]

for m in re.finditer(r'([^{}]*panel[^{}]*)\{([^}]*)\}', styles):
    print(f"Selector: {m.group(1).strip()}")
    print(f"Rules: {m.group(2).strip()[:100]}\n")

for line in style_content.split('\n'):
    if any(k in line for k in ['#panel-charts', '#panel-reco', '#panel-options', '#panel-notifications']):
        print(line[:120])
