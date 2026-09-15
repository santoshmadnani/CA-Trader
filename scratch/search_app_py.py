from pathlib import Path
import re

text = Path('app.py').read_text(encoding='utf-8')
for term in ['vix', 'dow', 'gift', 'other-factors', 'macro', 'breadth']:
    matches = list(re.finditer(re.escape(term), text, re.I))
    print(f"app.py term '{term}': {len(matches)}")

