with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

# find recommendation logic for options
matches = re.findall(r'def\s+(?:overall_recommendation|analysis_overall|get_recommendation)[^:]*:', text)
print("Recommendation endpoints/functions:", matches)

# search for "CE" or "PE" in overall_recommendation
m = re.search(r'def\s+overall_recommendation\s*\([^)]*\):', text)
if m:
    print("overall_recommendation snippet:\n", text[m.start():m.start()+2500])

