with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for fn in ['loadOptions', 'loadNews', 'loadNewsByCaAi', 'loadFundamentals', 'loadOtherFactorsSuite', 'loadMovers', 'loadRecommendations']:
    matches = [m.start() for m in re.finditer(r'function\s+' + fn, text)]
    print(f"Function {fn}: {len(matches)} definitions found at chars {matches}")

