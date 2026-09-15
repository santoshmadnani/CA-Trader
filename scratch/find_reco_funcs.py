from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
for m in re.finditer(r'function\s+([a-zA-Z0-9_]*reco[a-zA-Z0-9_]*)\b', text, re.I):
    print("Function:", m.group(1))

matches = list(re.finditer(r'function\s+loadDashboard\b', text))
if matches:
    print("loadDashboard at char:", matches[0].start())
    print(text[matches[0].start():matches[0].start()+1500])

