from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
for term in ['confluence', 'multi-factor', 'high conviction', 'dashrationale', 'rationale modal', 'show rationale']:
    matches = list(re.finditer(re.escape(term), text, re.IGNORECASE))
    print(f"Term '{term}': {len(matches)} occurrences")
    for m in matches[:3]:
        line = text[:m.start()].count('\n') + 1
        print(f"  Line {line}: {text[max(0, m.start()-40):min(len(text), m.end()+40)].strip()}")

