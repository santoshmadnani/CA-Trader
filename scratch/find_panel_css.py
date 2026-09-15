from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
style_end = text.find('</style>')
styles = text[:style_end]

for m in re.finditer(r'([^{}]*panel[^{}]*)\{([^}]*)\}', styles):
    print(f"Selector: {m.group(1).strip()}")
    print(f"Rules: {m.group(2).strip()[:100]}\n")

