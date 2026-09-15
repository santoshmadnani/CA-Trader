from pathlib import Path
import re

text = Path('terminal.html').read_text(encoding='utf-8')
for fn in ['populateRecoOptionDropdown', 'applyOptionRecommendation', 'updateChartRecoBanner']:
    pos = text.find(f'function {fn}')
    if pos != -1:
        line = text[:pos].count('\n') + 1
        print(f"--- {fn} at line {line} ---")
        print(text[pos:pos+1500])

